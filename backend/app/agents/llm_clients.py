"""External AI and search clients for the knowledge agent."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from app.core.config import settings


class AIProviderError(RuntimeError):
    pass


def _auth_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _require(value: str, name: str) -> str:
    if not value:
        raise AIProviderError(f"未配置 {name}，请在后端 .env 中填写")
    return value


def _chat_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/chat/completions"


async def analyze_image_with_qwen(
    question: str,
    images: list[dict[str, str]],
    *,
    observation_only: bool = False,
) -> str:
    api_key = _require(settings.QWEN_VL_API_KEY or settings.VL_API_KEY, "QWEN_VL_API_KEY")
    if observation_only:
        prompt = (
            "你是农业病虫害图片观察助手。请综合用户上传的一张或多张图片，"
            "只记录图片中能够直接观察到的事实，不要直接下最终病害诊断。"
            "请用中文简洁输出："
            "1. 疑似病虫害名称：根据可见症状给出1-3个最可能的病/虫害名称（标注'疑似'，仅供检索参考，不作为最终诊断）；"
            "2. 作物或器官、受害部位、颜色和形状、病斑边界、是否有水渍/霉层/虫体/虫粪、果实或叶片的异常变化；"
            "3. 无法确认的地方。"
            "如果无法识别，请明确说无法识别，并说明需要用户补充哪些文字描述。"
            f"\n用户文字：{question or '用户未提供文字描述'}"
        )
    else:
        prompt = (
            "你是农业图片识别助手。请综合用户上传的一张或多张图片，识别其中的农业相关内容，重点判断是否为农药、化肥、种子、"
            "农资产品、作物、病虫害症状或其他农业场景。"
            "请用中文简洁输出：识别结论、可能名称、关键信息、无法确认的地方。"
            "如果无法识别，请明确说无法识别，并说明需要用户补充哪些文字描述。"
            f"\n用户文字：{question or '用户未提供文字描述'}"
        )
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for image in images:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{image['mime_type']};base64,{image['base64']}"},
        })
    payload = {
        "model": settings.QWEN_VL_MODEL,
        "messages": [
            {
                "role": "user",
                "content": content,
            }
        ],
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=45.0) as client:
        base_url = settings.VL_BASE_URL or settings.QWEN_VL_BASE_URL
        response = await client.post(_chat_url(base_url), headers=_auth_headers(api_key), json=payload)
    if response.status_code >= 400:
        raise AIProviderError(f"图片识别失败：{response.text[:300]}")
    data = response.json()
    return data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()


async def tavily_search(query: str) -> list[dict[str, str]]:
    api_key = _require(settings.TAVILY_API_KEY, "TAVILY_API_KEY")
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "advanced",
        "max_results": 8,
        "include_answer": False,
        "include_raw_content": False,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post("https://api.tavily.com/search", json=payload)
    if response.status_code >= 400:
        raise AIProviderError(f"Tavily 搜索失败：{response.text[:300]}")
    data = response.json()
    results = data.get("results") or []
    return [
        {
            "title": str(item.get("title") or "未命名来源"),
            "url": str(item.get("url") or ""),
            "content": str(item.get("content") or "")[:900],
        }
        for item in results
        if item.get("url") and item.get("content")
    ]


async def stream_deepseek(messages: list[dict[str, Any]]) -> AsyncGenerator[str, None]:
    api_key = _require(settings.DEEPSEEK_API_KEY, "DEEPSEEK_API_KEY")
    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.35,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream(
            "POST",
            _chat_url(settings.DEEPSEEK_BASE_URL),
            headers=_auth_headers(api_key),
            json=payload,
        ) as response:
            if response.status_code >= 400:
                body = await response.aread()
                raise AIProviderError(f"DeepSeek 生成失败：{body.decode('utf-8', errors='ignore')[:300]}")
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line.removeprefix("data:").strip()
                if data == "[DONE]":
                    break
                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = payload.get("choices", [{}])[0].get("delta", {}).get("content")
                if delta:
                    yield delta
