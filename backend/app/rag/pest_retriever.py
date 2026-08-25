"""Retriever for pest and disease knowledge."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import PestKnowledge
from app.rag.embedding_service import embedding_service
from app.rag.milvus_client import search_pest_vectors


logger = logging.getLogger("pest_rag")


QUERY_ALIASES = {
    "西红柿": "番茄",
    "蕃茄": "番茄",
    "土豆": "马铃薯",
    "洋芋": "马铃薯",
}


def normalize_query_text(text: str) -> str:
    normalized = text or ""
    for alias, canonical in QUERY_ALIASES.items():
        normalized = normalized.replace(alias, canonical)
    return normalized


@dataclass
class PestKnowledgeMatch:
    knowledge: PestKnowledge
    score: float


def compose_pest_vector_text(knowledge: PestKnowledge) -> str:
    """向量化文本：保留检索相关字段，聚焦症状与病名 + 语义补充字段。

    - 召回用：crop/pest_name/intro/symptoms/morphology/cause/habit
    - 排除 control_method：是答案不是检索词，且部分含"参见XX病"字样会污染向量
    - 排除 category：无语义价值
    - cause/habit 含"群集/迁飞/高温高湿"等语义信号，能桥接 VL 口语描述与学术用语
    - 核心症状字段靠前，补充字段靠后，极端长文本截断时先丢补充字段
    - 命中后 format_matches_for_prompt 从 MySQL 取完整字段给 LLM，不丢信息
    """
    return "\n".join([
        f"作物：{knowledge.crop_name}",
        f"病虫害名称：{knowledge.pest_name}",
        f"简介：{knowledge.intro or ''}",
        f"危害症状：{knowledge.symptoms or ''}",
        f"形态特征：{knowledge.morphology or ''}",
        f"发生因素：{knowledge.cause or ''}",
        f"生活习性：{knowledge.habit or ''}",
    ]).strip()


def search_pest_knowledge(
    db: Session,
    query_text: str,
    *,
    extra_queries: list[str] | None = None,
) -> tuple[list[PestKnowledgeMatch], str | None]:
    """搜索病虫害知识库。

    支持多查询合并：主查询 + 额外聚焦查询（如提取的病名），
    取每条知识的最高分，提升跨模态（VL 描述 → 知识库结构化文本）命中率。
    """
    queries = [query_text]
    if extra_queries:
        for q in extra_queries:
            q = q.strip()
            if q and q not in queries:
                queries.append(q)

    # knowledge_id -> (match, score)，保留每条知识的最高分
    best_by_id: dict[int, PestKnowledgeMatch] = {}

    for idx, query in enumerate(queries):
        try:
            vector = embedding_service.embed_text(normalize_query_text(query))
            vector_matches = search_pest_vectors(vector, settings.PEST_RAG_TOP_K)
        except Exception as error:
            logger.warning("pest vector search failed (query#%d): %s", idx, error)
            if not best_by_id:
                return [], str(error)
            continue

        if not vector_matches:
            continue

        ids = [item["knowledge_id"] for item in vector_matches]
        knowledge_by_id = {
            item.id: item
            for item in db.query(PestKnowledge).filter(PestKnowledge.id.in_(ids)).all()
        }
        for item in vector_matches:
            knowledge = knowledge_by_id.get(item["knowledge_id"])
            if not knowledge:
                continue
            score = float(item["score"])
            existing = best_by_id.get(knowledge.id)
            if existing is None or score > existing.score:
                best_by_id[knowledge.id] = PestKnowledgeMatch(knowledge=knowledge, score=score)

    matches = sorted(best_by_id.values(), key=lambda m: m.score, reverse=True)

    if matches:
        top = matches[0]
        logger.info(
            "pest rag top match: id=%s crop=%s pest=%s score=%.4f (queries=%d, total_matches=%d)",
            top.knowledge.id, top.knowledge.crop_name, top.knowledge.pest_name,
            top.score, len(queries), len(matches),
        )
        for i, m in enumerate(matches[:3]):
            logger.debug(
                "  match[%d] score=%.4f crop=%s pest=%s",
                i, m.score, m.knowledge.crop_name, m.knowledge.pest_name,
            )

    return matches, None


def _pest_name_hit(pest_name: str, normalized_query: str) -> bool:
    """病名匹配：支持双向子串匹配，应对 VL 输出名称与知识库名称略有差异的情况。"""
    if not pest_name or not normalized_query:
        return False
    pest_name = normalize_query_text(pest_name)
    # 去掉"疑似"等前缀干扰
    query = normalized_query.replace("疑似", "")
    if pest_name in query:
        return True
    # 反向匹配：VL 输出的病名可能是知识库病名的子串（如"早疫病" vs "番茄早疫病"）
    # 拆分病名关键词，逐个检查是否出现在查询中
    keywords = [k for k in pest_name.replace("病", " ").replace("虫", " ").split() if len(k) >= 2]
    if keywords and all(k in query for k in keywords):
        return True
    return False


def is_confident_match(
    matches: list[PestKnowledgeMatch],
    query_text: str,
    *,
    extracted_pest_names: list[str] | None = None,
) -> bool:
    if not matches:
        return False
    top = matches[0]
    threshold = settings.PEST_RAG_SCORE_THRESHOLD
    if top.score >= threshold:
        logger.info("is_confident_match: score=%.4f >= threshold=%.4f => True", top.score, threshold)
        return True
    normalized_query = normalize_query_text(query_text)
    crop_hit = bool(
        top.knowledge.crop_name
        and top.knowledge.crop_name in normalized_query
    )
    pest_hit = _pest_name_hit(top.knowledge.pest_name, normalized_query)
    # VL 提取的疑似病名与知识库病名直接比对（最强信号）
    name_hit = False
    if extracted_pest_names:
        kb_name = normalize_query_text(top.knowledge.pest_name or "")
        for name in extracted_pest_names:
            name = normalize_query_text(name)
            if not name:
                continue
            if name in kb_name or kb_name in name:
                name_hit = True
                break
            # 去掉作物前缀后再比（如 "早疫病" vs "番茄早疫病"）
            core = name.replace("病", "").replace("虫", "").strip()
            kb_core = kb_name.replace("病", "").replace("虫", "").strip()
            if core and kb_core and (core in kb_core or kb_core in core):
                name_hit = True
                break
    # 宽松匹配：分数在 threshold-0.15 以上，且作物/病名/提取病名任一命中
    relaxed = threshold - 0.15
    result = bool(top.score >= relaxed and (crop_hit or pest_hit or name_hit))
    logger.info(
        "is_confident_match: score=%.4f threshold=%.4f relaxed=%.4f "
        "crop_hit=%s pest_hit=%s name_hit=%s => %s",
        top.score, threshold, relaxed, crop_hit, pest_hit, name_hit, result,
    )
    return result


def format_matches_for_prompt(matches: list[PestKnowledgeMatch]) -> str:
    if not matches:
        return "无本地病虫害知识库匹配结果。"
    chunks: list[str] = []
    for index, match in enumerate(matches, start=1):
        item = match.knowledge
        chunks.append(
            "\n".join([
                f"[{index}] 匹配分数：{match.score:.3f}",
                f"作物：{item.crop_name}",
                f"类型：{item.category}",
                f"名称：{item.pest_name}",
                f"简介：{item.intro or '无'}",
                f"危害症状：{item.symptoms or '无'}",
                f"发生因素：{item.cause or '无'}",
                f"防治方法：{item.control_method or '无'}",
            ])
        )
    return "\n\n".join(chunks)
