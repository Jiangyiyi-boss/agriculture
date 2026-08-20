"""Short-term AI conversation memory backed by Redis."""

from __future__ import annotations

import json
from typing import Any

import redis

from app.core.config import settings


class ShortTermMemory:
    """Stores the latest conversation turns in Redis, with graceful fallback."""

    def __init__(self) -> None:
        self._client: redis.Redis | None = None
        try:
            self._client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            self._client.ping()
        except Exception:
            self._client = None

    def _key(self, user_id: int, conversation_id: int) -> str:
        return f"ai:chat:{user_id}:{conversation_id}"

    def get_messages(self, user_id: int, conversation_id: int) -> list[dict[str, str]]:
        if not self._client:
            return []
        raw = self._client.get(self._key(user_id, conversation_id))
        if not raw:
            return []
        try:
            messages = json.loads(raw)
            return messages if isinstance(messages, list) else []
        except json.JSONDecodeError:
            return []

    def save_messages(self, user_id: int, conversation_id: int, messages: list[dict[str, Any]]) -> None:
        if not self._client:
            return
        max_messages = max(settings.AI_REDIS_MAX_ROUNDS, 1) * 2
        compact = [
            {"role": item.get("role", ""), "content": item.get("content", "")}
            for item in messages
            if item.get("role") in {"user", "assistant"} and item.get("content")
        ][-max_messages:]
        self._client.setex(
            self._key(user_id, conversation_id),
            settings.AI_REDIS_TTL_SECONDS,
            json.dumps(compact, ensure_ascii=False),
        )

    def delete_messages(self, user_id: int, conversation_id: int) -> None:
        """删除某个会话的短期记忆（删除会话时调用）"""
        if not self._client:
            return
        self._client.delete(self._key(user_id, conversation_id))


memory = ShortTermMemory()

