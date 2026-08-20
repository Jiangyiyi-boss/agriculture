"""AI 长期记忆：独立事实条目的提取与注入（MySQL 存储）"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.agents.llm_clients import AIProviderError, _auth_headers, _chat_url, _require
from app.core.config import settings
from app.models import AiMemory

logger = logging.getLogger("long_term_memory")

MAX_MEMORIES_PER_USER = 30

EXTRACT_SYSTEM_PROMPT = (
    "你是记忆提取器。根据农户本轮问答和已有记忆列表，提取关于该农户的稳定事实（地区、种植面积、"
    "种植作物及品种、种植目标、关注病虫害、经验水平、偏好等）。\n"
    "规则：\n"
    "1. 只提取问答中明确出现的稳定事实，忽略一次性的寒暄、临时性问题和纯知识咨询（农户问'稻瘟病怎么治'不代表他种水稻，除非问答中有明确信息）\n"
    "2. 新事实 → add；与旧条目冲突或可补充 → update（给出完整新内容）；旧信息已过时失效 → delete\n"
    "3. 每条事实一句话、具体简洁（如'在长沙岳麓区种植水稻约2亩'）\n"
    "4. 没有值得提取的内容时，所有数组留空\n"
    '严格输出 JSON：{"add": ["..."], "update": [{"id": 1, "content": "..."}], "delete": [2]}'
)


def get_memory_items(db: Session, user_id: int) -> list[AiMemory]:
    return db.query(AiMemory).filter(AiMemory.user_id == user_id).order_by(
        AiMemory.created_at.asc(),
    ).limit(MAX_MEMORIES_PER_USER).all()


def format_memory_prompt(db: Session, user_id: int) -> str:
    """把该用户的记忆条目格式化为注入 system prompt 的文本；无记忆返回空串"""
    items = get_memory_items(db, user_id)
    if not items:
        return ""
    lines = "\n".join(f"- {item.content}" for item in items)
    return f"\n\n该农户的长期记忆（历史对话提炼的画像，供个性化回答参考，注意与用户当前表述冲突时以当前为准）：\n{lines}"


async def _call_extraction_llm(messages: list[dict[str, Any]]) -> str:
    """非流式调用 DeepSeek 提取记忆（复用 llm_clients 的配置）"""
    api_key = _require(settings.DEEPSEEK_API_KEY, "DEEPSEEK_API_KEY")
    base_url = _require(settings.DEEPSEEK_BASE_URL, "DEEPSEEK_BASE_URL")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            _chat_url(base_url),
            headers=_auth_headers(api_key),
            json={
                "model": settings.DEEPSEEK_MODEL,
                "messages": messages,
                "temperature": 0.1,
                "max_tokens": 800,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


async def extract_and_update_memories(
    db: Session,
    *,
    user_id: int,
    conversation_id: int,
    question: str,
    answer: str,
) -> None:
    """每轮问答后异步提取记忆：新增/更新/删除独立条目。失败静默，不影响主流程。"""
    if not question or not answer:
        return
    try:
        existing = get_memory_items(db, user_id)
        existing_text = "\n".join(f"[id={item.id}] {item.content}" for item in existing) or "（暂无记忆）"
        # 限制输入长度，避免长回答撑爆 token
        q = question[:500]
        a = answer[:2000]
        messages = [
            {"role": "system", "content": EXTRACT_SYSTEM_PROMPT},
            {"role": "user", "content": f"已有记忆：\n{existing_text}\n\n本轮农户提问：{q}\n\n本轮回答：{a}"},
        ]
        raw = await _call_extraction_llm(messages)
        plan = json.loads(raw)
        add_list = [str(item).strip() for item in plan.get("add", []) if str(item).strip()]
        update_list = plan.get("update", [])
        delete_ids = [int(i) for i in plan.get("delete", []) if str(i).isdigit()]
        existing_ids = {item.id for item in existing}

        for content in add_list[:10]:
            db.add(AiMemory(user_id=user_id, content=content[:500], conversation_id=conversation_id))
        for item in update_list[:10]:
            try:
                mid = int(item.get("id"))
                content = str(item.get("content", "")).strip()
            except (TypeError, ValueError):
                continue
            if mid in existing_ids and content:
                target = db.query(AiMemory).filter(AiMemory.id == mid, AiMemory.user_id == user_id).first()
                if target:
                    target.content = content[:500]
        for mid in delete_ids:
            if mid in existing_ids:
                db.query(AiMemory).filter(AiMemory.id == mid, AiMemory.user_id == user_id).delete()
        db.commit()
    except (httpx.HTTPError, AIProviderError, json.JSONDecodeError, KeyError, ValueError) as error:
        db.rollback()
        logger.warning("记忆提取失败（不影响问答）: %s", error)
