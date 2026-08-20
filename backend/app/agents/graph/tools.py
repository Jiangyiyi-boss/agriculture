"""LangGraph tools for the ReAct agent.

Each tool is a self-contained function that the LLM can call.
Tools receive `config: RunnableConfig` to access runtime dependencies (db, user, images).
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.agents.llm_clients import analyze_image_with_qwen, tavily_search
from app.agents.long_term_memory import format_memory_prompt
from app.models import CropManagement
from app.rag.pest_retriever import (
    format_matches_for_prompt,
    is_confident_match,
    search_pest_knowledge,
)
from app.rag.planting_retriever import run_rule_engine

logger = logging.getLogger("graph.tools")


def _get_configurable(config: RunnableConfig, key: str, default: Any = None) -> Any:
    return config.get("configurable", {}).get(key, default)


# ---------------------------------------------------------------------------
# 网络错误重试机制：只对临时性故障重试，业务错误直接抛出
# ---------------------------------------------------------------------------

# 可重试的错误类型：网络连接、超时
RETRYABLE_ERRORS = (ConnectionError, TimeoutError, asyncio.TimeoutError)


async def _retry_on_network_error(
    coro_factory: Any,
    *,
    max_attempts: int = 3,
    delay: float = 1.0,
    tool_name: str = "",
) -> Any:
    """对网络类错误自动重试，其他错误直接抛出。

    Args:
        coro_factory: 无参数的可调用对象，每次调用返回一个新协程
        max_attempts: 最大尝试次数（含首次）
        delay: 重试间隔（秒）
        tool_name: 工具名（用于日志）

    Returns:
        协程的返回值

    Raises:
        网络错误超过重试次数后抛出最后一次的异常；
        非网络错误立即抛出（不重试）。
    """
    last_error: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return await coro_factory()
        except RETRYABLE_ERRORS as exc:
            last_error = exc
            if attempt < max_attempts - 1:
                logger.warning(
                    "%s 第%d/%d次调用失败（网络错误：%s），%.1f秒后重试...",
                    tool_name, attempt + 1, max_attempts, exc, delay,
                )
                await asyncio.sleep(delay)
            else:
                logger.warning(
                    "%s 已达最大重试次数 %d，放弃：%s",
                    tool_name, max_attempts, exc,
                )
        # 非网络错误不捕获，直接向上抛（外层 try/except 处理）
    raise last_error  # type: ignore[misc]


# ---------------------------------------------------------------------------
# 搜索质量控制和上下文注入（从 knowledge_agent.py 迁移）
# ---------------------------------------------------------------------------

AUTHORITY_HINTS = (
    ".gov.cn", "moa.gov.cn", "agri", "农业农村", "农技", "农科院", "植保", "推广", "edu.cn"
)
LOW_QUALITY_HINTS = ("广告", "加盟", "招商", "采购", "批发", "厂家直销")
CONTEXT_REQUIRED_HINTS = ("我这里", "当地", "本地", "这边", "现在适合", "适合种", "能不能种", "什么时候种")
CONTEXT_OPTIONAL_HINTS = ("现在", "最近", "怎么治", "施什么肥", "防治", "播种", "采收", "病", "虫", "肥")

# 特色作物类问题：走多轮聚焦搜索（特色作物 / 特产 / 地理标志），避免被"使用方法用量"后缀干扰
SPECIALTY_KEYWORDS = ("特色作物", "特产", "名优", "特色农产品", "地理标志", "本地特色", "特色种植")


@dataclass
class UserContext:
    region: str
    active_crops: list[str]


def get_user_context(db, user) -> UserContext:
    """查询用户的地区和正在种植的作物（最多5种）。"""
    crops = db.query(CropManagement).filter(
        CropManagement.user_id == user.id,
        CropManagement.status == "种植中",
    ).order_by(CropManagement.updated_at.desc()).limit(5).all()
    crop_names = []
    for crop in crops:
        if crop.name and crop.name not in crop_names:
            crop_names.append(crop.name)
    return UserContext(region=user.region or "", active_crops=crop_names)


def should_use_user_context(question: str, context: UserContext) -> bool:
    """判断是否应该把用户地区/作物信息注入搜索词。"""
    if not question or not (context.region or context.active_crops):
        return False
    if any(hint in question for hint in CONTEXT_REQUIRED_HINTS):
        return True
    if any(crop and crop in question for crop in context.active_crops):
        return True
    return bool(any(hint in question for hint in CONTEXT_OPTIONAL_HINTS) and (context.region or context.active_crops))


def build_search_query(question: str, context: UserContext) -> str:
    """构造搜索词，必要时注入用户地区和作物信息。"""
    parts: list[str] = []
    if should_use_user_context(question, context):
        if context.region:
            parts.append(context.region)
        matched_crops = [crop for crop in context.active_crops if crop and crop in question]
        if matched_crops:
            parts.extend(matched_crops[:2])
        elif context.active_crops and any(hint in question for hint in ("我这里", "当地", "本地", "现在", "施什么肥")):
            parts.extend(context.active_crops[:2])
    if question:
        parts.append(question)
    parts.append("农业 农技 使用方法 用量 注意事项")
    return " ".join(part for part in parts if part).strip()


def is_specialty_question(question: str) -> bool:
    """检测是否是"特色作物/特产"类问题（走多轮搜索覆盖更全）。"""
    return any(kw in question for kw in SPECIALTY_KEYWORDS)


def extract_place_from_question(question: str) -> str:
    """从问题中提取连续地名串，如 '全州县枧塘镇有什么特色作物' → '全州县枧塘镇'。"""
    if not question:
        return ""
    match = re.search(
        r"[\u4e00-\u9fa5]+?(?:省|市|县|区)([\u4e00-\u9fa5]+?(?:镇|乡|街道))?",
        question,
    )
    return match.group(0) if match else ""


def build_specialty_search_queries(question: str, context: UserContext) -> list[str]:
    """特色作物类问题：构造多个聚焦搜索词。"""
    place = extract_place_from_question(question)
    if not place and context.region:
        place = context.region.replace(" ", "")
    if not place:
        return [question]
    return [
        f"{place} 特色作物",
        f"{place} 特产",
        f"{place} 地理标志农产品",
    ]


def filter_sources(sources: list[dict[str, str]], max_results: int = 5) -> list[dict[str, str]]:
    """过滤搜索结果：优先权威来源、剔除广告垃圾、去重。"""
    def score(item: dict[str, str]) -> int:
        haystack = f"{item.get('title', '')} {item.get('url', '')} {item.get('content', '')}"
        value = 0
        if any(hint in haystack for hint in AUTHORITY_HINTS):
            value += 4
        if any(hint in haystack for hint in LOW_QUALITY_HINTS):
            value -= 5
        if len(item.get("content", "")) > 120:
            value += 1
        return value

    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for item in sorted(sources, key=score, reverse=True):
        url = item.get("url", "")
        if url in seen or score(item) < -2:
            continue
        seen.add(url)
        unique.append(item)
        if len(unique) >= max_results:
            break
    return unique


def format_sources_for_prompt(sources: list[dict[str, str]]) -> str:
    """把搜索结果格式化为文本，供 LLM 阅读。"""
    if not sources:
        return "联网搜索未返回结果。"
    lines = []
    for i, s in enumerate(sources, 1):
        title = s.get("title", "未命名")
        content = s.get("content", "")[:300]
        lines.append(f"[{i}] {title}\n摘要：{content}")
    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# rag_search — 病虫害知识库（Milvus 向量检索）
# ---------------------------------------------------------------------------

@tool
async def rag_search(query: str, config: RunnableConfig) -> str:
    """搜索病虫害知识库（Milvus向量检索）。

    输入病虫害症状描述或疑似病虫害名称，返回匹配的病虫害知识（诊断、症状、防治方法）。
    适用场景：用户上传了病虫害图片或描述了病害/虫害症状。

    Args:
        query: 症状描述文本，如"番茄叶子有黄斑，叶背有霉层"
    """
    db = _get_configurable(config, "db")
    if not db:
        return "错误：数据库连接不可用"

    try:
        # search_pest_knowledge 是同步函数，放到线程池执行
        # 网络错误（Milvus 连接超时等）自动重试 3 次
        matches, error = await _retry_on_network_error(
            lambda: asyncio.to_thread(search_pest_knowledge, db, query),
            tool_name="rag_search",
        )
        if error:
            return f"病虫害知识库检索失败：{error}"
        if not matches:
            return "未在本地病虫害知识库中找到匹配结果。"
        if not is_confident_match(matches, query):
            # 返回结果但标注置信度不足
            result = format_matches_for_prompt(matches)
            return f"以下匹配结果置信度不足，仅供参考：\n{result}"
        return format_matches_for_prompt(matches)
    except RETRYABLE_ERRORS as exc:
        logger.warning("rag_search 重试3次后仍失败: %s", exc)
        return "病虫害知识库暂时不可用（网络故障），建议改用 web_search 搜索相关资料。"
    except Exception as exc:
        logger.warning("rag_search 失败: %s", exc)
        return f"病虫害知识库检索异常：{exc}"


# ---------------------------------------------------------------------------
# web_search — 联网搜索（Tavily）
# ---------------------------------------------------------------------------

@tool
async def web_search(query: str, config: RunnableConfig) -> str:
    """联网搜索农业资料。

    在互联网上搜索农业相关的知识、新闻、技术资料。
    适用场景：需要补充知识库未覆盖的信息、查询最新农业政策、市场行情、通用农技知识、特色作物。

    会自动根据用户所在地区和种植作物优化搜索词，并过滤广告类低质量结果、
    优先返回政府/农技等权威来源。特色作物类问题会走多轮聚焦搜索。

    Args:
        query: 搜索词，如"湖南 8月 适合种什么作物"或"全州县有什么特色作物"
    """
    db = _get_configurable(config, "db")
    user = _get_configurable(config, "user")

    async def _tavily_with_retry(q: str) -> list[dict[str, str]]:
        """对 Tavily 搜索加重试。"""
        return await _retry_on_network_error(
            lambda: tavily_search(q),
            tool_name="web_search",
        )

    try:
        # 获取用户上下文（地区+种植作物）
        context = get_user_context(db, user) if db and user else UserContext(region="", active_crops=[])

        # 特色作物类问题：多轮聚焦搜索
        if is_specialty_question(query):
            search_queries = build_specialty_search_queries(query, context)
            # 每个子搜索独立重试，互不影响
            results_lists = await asyncio.gather(
                *[_tavily_with_retry(sq) for sq in search_queries]
            )
            all_sources: list[dict[str, str]] = []
            for results in results_lists:
                all_sources.extend(results)
            sources = filter_sources(all_sources, max_results=8)
        else:
            # 普通问题：注入用户上下文后单次搜索
            enhanced_query = build_search_query(query, context)
            sources = filter_sources(await _tavily_with_retry(enhanced_query))

        # 把来源存入收集器，供前端展示"参考资料"卡片
        collector = _get_configurable(config, "sources_collector")
        if isinstance(collector, list) and sources:
            collector.extend(
                {
                    "title": s.get("title", "未命名"),
                    "url": s.get("url", ""),
                    "content": s.get("content", "")[:200],
                }
                for s in sources
            )

        return format_sources_for_prompt(sources)
    except RETRYABLE_ERRORS as exc:
        logger.warning("web_search 重试3次后仍失败: %s", exc)
        return "联网搜索暂时不可用（网络故障），请稍后重试。"
    except Exception as exc:
        logger.warning("web_search 失败: %s", exc)
        return f"联网搜索失败：{exc}"


# ---------------------------------------------------------------------------
# analyze_image — 图片分析（Qwen VL）
# ---------------------------------------------------------------------------

@tool
async def analyze_image(query: str, config: RunnableConfig) -> str:
    """分析用户上传的农业图片。

    用视觉模型识别图片中的作物、病虫害症状、农资产品等。
    适用场景：用户上传了图片时，应先调用此工具获取图片信息。

    Args:
        query: 对图片的补充说明，如"这是番茄叶片，请重点观察病斑"
    """
    images = _get_configurable(config, "images", [])
    if not images:
        return "用户未上传图片，无需分析。"

    try:
        # Qwen-VL API 调用，网络错误自动重试 3 次
        result = await _retry_on_network_error(
            lambda: analyze_image_with_qwen(query, images, observation_only=True),
            tool_name="analyze_image",
        )
        return result or "图片分析未返回有效结果。"
    except RETRYABLE_ERRORS as exc:
        logger.warning("analyze_image 重试3次后仍失败: %s", exc)
        return "图片分析暂时不可用（网络故障），请稍后重试或用文字描述症状。"
    except Exception as exc:
        logger.warning("analyze_image 失败: %s", exc)
        return f"图片分析失败：{exc}"


# ---------------------------------------------------------------------------
# rule_engine — 种植规则引擎（MySQL 结构化查询）
# ---------------------------------------------------------------------------

@tool
async def rule_engine(query: str, config: RunnableConfig) -> str:
    """种植规则引擎：根据地区、土壤、月份筛选适配作物。

    查询数据库中的作物适宜性、土壤数据、行政区划，返回适配作物列表。
    适用场景：用户询问"种什么"、"怎么种"、"轮作"等种植计划相关问题。

    Args:
        query: 用户的原始问题文本，引擎会从中提取地区、月份、目标等信息
    """
    db = _get_configurable(config, "db")
    user = _get_configurable(config, "user")
    if not db or not user:
        return "错误：无法获取用户信息或数据库连接。"

    try:
        # MySQL 查询可能超时，网络错误自动重试 3 次
        result = await _retry_on_network_error(
            lambda: asyncio.to_thread(run_rule_engine, db, user, query),
            tool_name="rule_engine",
        )
    except RETRYABLE_ERRORS:
        # 重试失败时降级到直接调用（当前线程）
        result = run_rule_engine(db, user, query)

    if not result:
        return "规则引擎未返回结果。"

    # 格式化输出
    lines = []
    lines.append(f"意图：{result.intent}")
    lines.append(f"地区：{result.region.province or ''} {result.region.city or ''} {result.region.county or ''}".strip())
    lines.append(f"面积：{result.area}亩" if result.area else "面积：未知")
    lines.append(f"目标：{result.goal}")
    if result.month:
        lines.append(f"月份：{result.month}月")

    if result.intent == "plan" and result.suitability:
        s = result.suitability
        if s.crop:
            lines.append(f"指定作物：{s.crop.crop_name}")
            lines.append(f"合理性：{'适合' if s.is_suitable else '不太适合'}")
            if s.mismatches:
                lines.append(f"不匹配原因：{'; '.join(s.mismatches)}")
            if s.reasons:
                lines.append(f"匹配理由：{'; '.join(s.reasons)}")
            if s.crop.sow_seasons:
                lines.append(f"播种季节：{s.crop.sow_seasons}")
            if s.crop.yield_ref:
                lines.append(f"丰产参考亩产：{s.crop.yield_ref}，实际受土壤、管理、气候影响会浮动")
                if s.crop.is_perennial and s.crop.category == "水果":
                    lines.append("注意：该产量为盛果期成年树参考，幼树挂果较少")

    elif result.intent == "rotation" and result.rotation_by_season:
        for season, crops in result.rotation_by_season.items():
            names = "、".join(c.crop_name for c in crops[:6])
            lines.append(f"{season}：{names}")

    elif result.candidates:
        lines.append("适配作物（按打分排序）：")
        for i, c in enumerate(result.candidates[:5], 1):
            crop = c.crop
            parts = [f"{i}. {crop.crop_name}（{crop.category}）", f"打分：{c.score}"]
            if crop.yield_ref:
                parts.append(f"丰产参考：{crop.yield_ref}")
                if crop.is_perennial and crop.category == "水果":
                    parts.append("盛果期参考，幼树少")
            if crop.sow_seasons:
                parts.append(f"播期：{crop.sow_seasons}")
            if c.reasons:
                parts.append(f"理由：{'、'.join(c.reasons)}")
            lines.append(" | ".join(parts))
        lines.append('注：以上亩产均为丰产参考值，实际产量受土壤、管理、气候条件影响会存在浮动。标注"盛果期参考"的为多年生果树成年树产量，幼树挂果较少。')

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 工具集合
# ---------------------------------------------------------------------------

ALL_TOOLS = [rag_search, web_search, analyze_image, rule_engine]