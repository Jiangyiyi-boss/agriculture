"""LangGraph ReAct agent entry point.

Architecture:
  create_react_agent (ReAct pattern)
    - LLM 自主决策调用哪个工具、调用顺序、是否需要多轮调用
    - 4 个工具：rag_search / web_search / analyze_image / rule_engine
    - 替代了早期的 router_agent + 3 个独立 Agent 架构
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.prebuilt import create_react_agent
from langgraph.store.postgres.aio import AsyncPostgresStore
from langmem import create_manage_memory_tool, create_search_memory_tool

from app.agents.graph.tools import ALL_TOOLS
from app.core.config import settings

logger = logging.getLogger("graph")

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """你是慧农宝的 AI 智能助手，面向农户提供农业知识问答、病虫害诊断、种植计划推荐。

## 你的能力
你可以使用以下工具获取信息：
- **rag_search**：搜索本地病虫害知识库（症状→诊断和防治方法）
- **web_search**：联网搜索农业资料（最新政策、市场行情、通用农技）
- **analyze_image**：分析用户上传的图片（识别作物、病虫害症状、农资产品）
- **rule_engine**：种植规则引擎（根据地区+土壤+月份筛选适配作物，评估种植合理性）

## 工作流程
1. 用户上传了图片 → 先调用 analyze_image 获取图片识别结果（作物/症状/农资产品等）
2. 病虫害诊断 → 将 analyze_image 返回的症状描述作为 rag_search 的查询依据，
   用知识库结果交叉验证图片识别，禁止仅凭图片就下诊断结论；不够再调用 web_search 补充
3. 种植计划（种什么/怎么种/轮作）→ 先调用 rule_engine，再调用 web_search 补充
4. 通用知识（农药用法/施肥/农技）→ 调用 web_search
   - 若用户上传了农资产品图片（农药/化肥包装），先将 analyze_image 识别出的产品名称
     作为 web_search 的查询依据，再基于搜索结果回答用法用量
5. 跨领域问题（如"诊断病害后推荐替代作物"）→ 依次调用相关工具
6. 农事操作建议（播种/采收/施肥/浇水/苗期管理/病虫害防治等）→ 必须调用 web_search
   结合当前季节给出建议，禁止仅凭印象回答
7. 只有以下情况可以直接回答，不调用工具：
   - 问候、闲聊、感谢
   - 对上一轮回答的追问（如"再说清楚点"）

## 回答要求
- 用通俗易懂、务实的中文回答，语气亲切，称呼用户用"您"或"老乡"
- 回答简洁务实，一般控制在 300 字以内；步骤较多的防治方案可适当延长，但不超过 600 字
- 用短句和分点表达，避免大段文字
- 不要编造姓氏或姓名（如"老廖""张师傅"）
- 种植计划：产量数据必须依据 rule_engine 提供的丰产参考亩产 × 种植面积计算，严禁说"您一定能收 XX 公斤"，应表述为"丰产参考亩产 XX 公斤"
- 涉及产量的回答，末尾必须附加提示："以上为丰产参考产量，实际产量受土壤、管理、气候条件会存在浮动。"
- 遇到多年生果树（柑橘、猕猴桃、苹果、梨、桃、荔枝、芒果等），额外补充："该产量为盛果期成年树参考，幼树挂果较少。"
- 不要在正文中输出参考来源 URL 或链接
- 禁止在回答里提及"知识库""查知识库""查本地库"等内部工具名称，
  直接给诊断结论即可；但若使用了 web_search 联网搜索，末尾须标注"（以上内容来自联网搜索）"

## 多轮对话
- 历史对话由系统自动注入，请主动关联上下文，避免重复已完成的诊断
- 识别到用户的稳定事实（地区、种植作物、面积、偏好等）时，主动调用 manage_memory 工具记录
- 被问到用户历史信息时，主动调用 search_memory 工具检索

## 病虫害诊断硬约束
1. 严格依据 rag_search 返回的知识库原文，禁止脑补或改写特征描述
   - 知识库怎么描述症状，就怎么转述，不要替换成相似但不同的词
   - 例：知识库说"粉状"不要说成"绒毛"；知识库说"灰褐色"不要说成"白色"
2. 食品安全规则：
   - 知识库明确写"不能食用"/"完全不能食用"时，回答必须完全遵从原文，严禁建议"洗净后可食用""处理一下能吃"等减轻风险的说法。
   - 若知识库没有写明食用风险，但返回文本描述果实、可食用茎叶出现霉层、粉霉、湿软腐烂，则同样禁止输出"洗净后可以食用"这类降低风险的表述；需要告知霉菌菌丝有可能侵入组织内部，清洗仅能去除表面孢子，无法清除内部侵染，不建议食用。
3. 易混病害区分：必须严格按知识库对每种病害的特征描述来匹配，
   不要用通用印象判断。不同作物上同一种病害表现可能不同，
   以知识库对该作物该病害的具体描述为准。
4. 病菌侵染深度：知识库提到"菌丝侵入""侵入果肉""果实硬化"等
   表示病菌已深入组织内部的描述时，应告知用户病菌已侵入内部，
   清洗或表面处理无法去除，不建议食用。
5. 不确定时：症状与知识库描述不符或图片不清晰，
   明确建议咨询当地农技站或上传更清晰图片。
6. 药剂输出约束：
   - 药剂名称、用法用量以知识库原文为准，禁止编造药剂种类与剂量；
   - 凡是提到农药，必须提醒：严格按照农药产品标签使用，确认为当前登记作物药剂，遵守安全间隔期；
   - 采收期临近时，优先推荐生物防治或物理防治，减少化学农药残留风险。
"""


# ---------------------------------------------------------------------------
# LLM — ChatOpenAI 指向 DeepSeek API（兼容 OpenAI 格式）
# ---------------------------------------------------------------------------

_llm = ChatOpenAI(
    model=settings.DEEPSEEK_MODEL,
    api_key=settings.DEEPSEEK_API_KEY,
    base_url=settings.DEEPSEEK_BASE_URL,
    temperature=0.35,
    streaming=True,
)


# ---------------------------------------------------------------------------
# Graph building — 懒初始化（首次调用时建 pg 表）
# ---------------------------------------------------------------------------

_pg_saver: AsyncPostgresSaver | None = None
_pg_store: AsyncPostgresStore | None = None


def _bge_m3_embed(texts: list[str]) -> list[list[float]]:
    """用 BGE-M3 模型做 embedding（同步，由 store 在线程池中调用）"""
    from app.rag.embedding_service import embedding_service
    return embedding_service.embed_texts(texts)


async def _init_pg_backends() -> None:
    """懒初始化 pg checkpointer + store（首次调用时建表）"""
    global _pg_saver, _pg_store
    if _pg_saver is not None and _pg_store is not None:
        return
    # 用连接池长期持有，避免 async with 退出后连接关闭
    from psycopg.rows import dict_row
    from psycopg_pool import AsyncConnectionPool

    pool = AsyncConnectionPool(
        conninfo=settings.PG_URL,
        max_size=20,
        kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        open=False,
    )
    await pool.open()

    _pg_saver = AsyncPostgresSaver(conn=pool)
    await _pg_saver.setup()  # 自动建 checkpoint 表

    _pg_store = AsyncPostgresStore(
        conn=pool,
        index={
            "dims": settings.EMBEDDING_DIM,  # 1024，复用 BGE-M3 维度
            "embed": _bge_m3_embed,
        },
    )
    await _pg_store.setup()  # 自动建 store 表


async def _get_agent():
    """懒加载 agent：首次调用初始化 pg 后端 + 注册 langmem 工具"""
    await _init_pg_backends()
    return create_react_agent(
        model=_llm,
        tools=[
            *ALL_TOOLS,
            create_manage_memory_tool(namespace=("memories",)),
            create_search_memory_tool(namespace=("memories",)),
        ],
        checkpointer=_pg_saver,
        store=_pg_store,
    )


async def _sanitize_chat_history(agent, config: RunnableConfig) -> None:
    """清理 checkpoint 里孤立的 AIMessage(tool_calls)。

    场景：上轮对话 LLM 已生成 tool_calls，但工具执行前/中异常退出
    （SQLAlchemy 事务失效、SSE 断流、服务器重启等），
    checkpoint 留下带 tool_calls 的 AIMessage 但无对应 ToolMessage。
    下轮 LangGraph 加载历史时校验失败，抛 INVALID_CHAT_HISTORY。

    策略：删除末尾孤立的 AIMessage(tool_calls)，保留前面的历史，
    让 LLM 基于完整上下文重新决策是否调用工具。
    官方文档：https://docs.langchain.com/oss/python/langgraph/errors/INVALID_CHAT_HISTORY
    """
    from langchain_core.messages import RemoveMessage

    try:
        state = await agent.aget_state(config)
    except Exception:
        return

    values = state.values or {}
    messages: list = values.get("messages", [])
    if not messages:
        return

    # 收集所有已被 ToolMessage 回答的 tool_call_id
    answered_ids: set[str] = set()
    for msg in messages:
        if getattr(msg, "type", "") == "tool":
            tc_id = getattr(msg, "tool_call_id", "") or ""
            if tc_id:
                answered_ids.add(tc_id)

    # 从末尾找最后一个 AIMessage，检查它的 tool_calls 是否都被回答
    for idx in range(len(messages) - 1, -1, -1):
        msg = messages[idx]
        if getattr(msg, "type", "") != "ai":
            continue
        tool_calls = getattr(msg, "tool_calls", None) or []
        if not tool_calls:
            break  # 最后一个 AIMessage 没有 tool_calls，历史是干净的
        orphan_ids = [
            tc.get("id") if isinstance(tc, dict) else getattr(tc, "id", "")
            for tc in tool_calls
        ]
        orphan_ids = [tid for tid in orphan_ids if tid and tid not in answered_ids]
        if not orphan_ids:
            break  # 所有 tool_calls 都被回答了
        # 有孤立的 tool_calls → 删掉这个 AIMessage
        msg_id = getattr(msg, "id", None)
        if not msg_id:
            break
        await agent.aupdate_state(
            config,
            {"messages": [RemoveMessage(id=msg_id)]},
        )
        logger.warning(
            "清理了孤立的 AIMessage(tool_calls)，未回答 ids: %s",
            orphan_ids,
        )
        return


# ---------------------------------------------------------------------------
# Streaming entry point
# ---------------------------------------------------------------------------

def _fetch_weather_brief(user) -> str:
    """同步获取用户所在地实时天气+预报简报（在线程池中调用），失败返回空串。

    直接调用高德天气 API，不依赖 push_agent（避免跨模块 import 失效）。
    """
    adcode = getattr(user, "adcode", None)
    if not adcode:
        return ""
    try:
        import httpx
        from app.core.config import settings

        api_key = settings.AMAP_WEB_SERVICE_KEY or settings.AMAP_API_KEY
        base = "https://restapi.amap.com/v3"
        common = {"key": api_key, "city": adcode, "output": "json"}

        with httpx.Client(timeout=6.0) as client:
            live_resp = client.get(f"{base}/weather/weatherInfo", params={**common, "extensions": "base"})
            forecast_resp = client.get(f"{base}/weather/weatherInfo", params={**common, "extensions": "all"})

        live_resp.raise_for_status()
        forecast_resp.raise_for_status()
        live_data = live_resp.json()
        forecast_data = forecast_resp.json()

        if live_data.get("status") != "1" or forecast_data.get("status") != "1":
            logger.warning(f"高德天气接口返回失败 live={live_data.get('info')} forecast={forecast_data.get('info')}")
            return ""

        lives = live_data.get("lives") or []
        forecasts = forecast_data.get("forecasts") or []
        live = lives[0] if lives else {}
        casts = (forecasts[0].get("casts") if forecasts else []) or []

        parts = [
            f"当地实时天气：{live.get('weather', '')}，气温{live.get('temperature', '')}℃，"
            f"{live.get('winddirection', '')}风{live.get('windpower', '')}级，"
            f"湿度{live.get('humidity', '')}%"
        ]
        tomorrow_parts = []
        for cast in casts[1:3]:
            date_str = str(cast.get("date", ""))[-5:].replace("-", "月")
            tomorrow_parts.append(
                f"{date_str}日{cast.get('dayweather', '')}"
                f"{cast.get('nighttemp', '')}~{cast.get('daytemp', '')}℃"
            )
        if tomorrow_parts:
            parts.append("未来两天：" + "，".join(tomorrow_parts))
        return "；".join(parts)
    except Exception:
        logger.warning("获取用户所在地天气失败，跳过天气注入", exc_info=False)
        return ""


async def run_agent_stream(
    *,
    db,
    user,
    conversation_id: int,
    question: str,
    images: list[dict],
) -> AsyncGenerator[dict[str, Any], None]:
    """Run the ReAct agent and yield SSE-compatible events.

    Yields dicts with keys: event, data
    """
    # 注入当前日期+季节+当地天气，让 LLM 结合时令给农事建议
    from app.core.timezone import now_china
    now = now_china()
    season_map = {1: "冬季", 2: "冬季", 3: "春季", 4: "春季", 5: "春季", 6: "夏季",
                  7: "夏季", 8: "夏季", 9: "秋季", 10: "秋季", 11: "秋季", 12: "冬季"}
    season = season_map.get(now.month, "")
    context_info = f"\n\n【当前时间：{now.year}年{now.month}月{now.day}日，{season}】"

    weather_brief = await asyncio.to_thread(_fetch_weather_brief, user)
    if weather_brief:
        context_info += f"\n【{weather_brief}】"

    if images and question:
        user_text = f"用户上传了 {len(images)} 张图片，并提问：{question}{context_info}"
    elif images:
        user_text = f"用户上传了 {len(images)} 张图片，请帮我分析{context_info}"
    else:
        user_text = f"{question}{context_info}"

    # 历史对话由 checkpointer 按 thread_id 自动恢复，不再手动拼装
    initial_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_text},
    ]

    answer_parts: list[str] = []
    tool_call_count = 0
    sources_collector: list[dict[str, str]] = []

    config: RunnableConfig = {
        "configurable": {
            "db": db,
            "user": user,
            "conversation_id": conversation_id,
            "images": images,
            "sources_collector": sources_collector,
            # checkpointer 按 thread_id 恢复对话状态
            "thread_id": f"{user.id}:{conversation_id}",
            # langmem 工具按 langgraph_user_id 隔离用户记忆命名空间
            "langgraph_user_id": str(user.id),
        },
        # 防止 LLM 死循环调工具：最多 15 步（agent ⇄ tools 循环）
        # 农业问答场景 3-5 次工具调用足够，15 次留安全余量
        "recursion_limit": 15,
    }

    try:
        agent = await _get_agent()
        # 清理上轮可能残留的孤立 AIMessage(tool_calls)，避免 INVALID_CHAT_HISTORY
        await _sanitize_chat_history(agent, config)
        async for event in agent.astream_events(
            {"messages": initial_messages},
            config=config,
            version="v2",
        ):
            kind = event.get("event", "")

            if kind == "on_tool_start":
                tool_call_count += 1
                tool_name = event.get("name", "")
                tool_labels = {
                    "rag_search": "正在检索病虫害知识库...",
                    "web_search": "正在联网搜索相关资料...",
                    "analyze_image": "正在分析上传的图片...",
                    "rule_engine": "正在分析土壤和作物适配条件...",
                    "manage_memory": "正在记录您的偏好信息...",
                    "search_memory": "正在检索您的历史信息...",
                }
                status = tool_labels.get(tool_name, f"正在调用 {tool_name}...")
                yield {"event": "status", "data": {"message": status}}

            elif kind == "on_chat_model_stream":
                chunk_data = event.get("data", {}).get("chunk", {})
                if hasattr(chunk_data, "content") and chunk_data.content:
                    content = chunk_data.content
                    if isinstance(content, str):
                        answer_parts.append(content)
                        yield {"event": "chunk", "data": {"content": content}}

    except Exception as exc:
        logger.exception("Agent 运行异常")
        # 回滚 db session，防止连接池中的失效连接导致后续请求全部失败
        try:
            db.rollback()
        except Exception:
            pass
        yield {"event": "error", "data": {"detail": str(exc)}}
        return

    answer = "".join(answer_parts)
    yield {
        "event": "done",
        "data": {
            "answer": answer,
            "tool_calls": tool_call_count,
            "sources": sources_collector,
        },
    }


__all__ = ["run_agent_stream", "run_agent_background", "stream_agent_events", "get_task_status"]


# ---------------------------------------------------------------------------
# 后台任务 + 事件队列：支持断点续传
# ---------------------------------------------------------------------------

_running_tasks: dict[str, dict[str, Any]] = {}


def _make_task_id(user_id: int, conversation_id: int) -> str:
    return f"{user_id}:{conversation_id}"


async def run_agent_background(
    *,
    db,
    user,
    conversation_id: int,
    question: str,
    images: list[dict],
    user_message_id: int | None = None,
) -> str:
    """后台跑 agent，跑完把答案落库到 AIMessage 表。

    HTTP 断开后任务继续跑，用户切页面回来 GET messages 能拉到完整答案。
    返回 task_id（用于 HTTP 层订阅/查询状态）。
    """
    task_id = _make_task_id(user.id, conversation_id)
    queue: asyncio.Queue = asyncio.Queue()
    _running_tasks[task_id] = {
        "queue": queue,
        "status": "running",
        "answer": "",
        "sources": [],
    }

    async def _runner():
        answer = ""
        sources: list[dict] = []
        try:
            async for event in run_agent_stream(
                db=db,
                user=user,
                conversation_id=conversation_id,
                question=question,
                images=images,
            ):
                evt = event.get("event", "")
                data = event.get("data", {})
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    pass
                if evt == "chunk":
                    answer += data.get("content", "")
                elif evt == "done":
                    answer = data.get("answer", answer)
                    sources = data.get("sources", [])
                elif evt == "error":
                    detail = data.get("detail", "AI 问答暂时不可用")
                    answer = f"抱歉，{detail}"
        except Exception as exc:
            logger.exception("后台 agent 任务异常 task_id=%s", task_id)
            answer = f"抱歉，AI 问答暂时不可用：{exc}"
            try:
                queue.put_nowait({"event": "error", "data": {"detail": str(exc)}})
            except asyncio.QueueFull:
                pass
        finally:
            _running_tasks[task_id]["status"] = "done"
            _running_tasks[task_id]["answer"] = answer
            _running_tasks[task_id]["sources"] = sources
            try:
                queue.put_nowait({"event": "_task_done", "data": {}})
            except asyncio.QueueFull:
                pass
            try:
                await _persist_assistant_message(db, conversation_id, user.id, answer, sources, user_message_id)
            except Exception:
                logger.exception("落库 assistant message 失败 task_id=%s", task_id)
            asyncio.get_event_loop().call_later(
                300, lambda: _running_tasks.pop(task_id, None)
            )

    asyncio.create_task(_runner())
    return task_id


async def _persist_assistant_message(
    db, conversation_id: int, user_id: int, answer: str,
    sources: list[dict], user_message_id: int | None,
) -> None:
    """把 agent 最终答案写入 AIMessage 表。"""
    import json
    from app.models import AIMessage

    msg = AIMessage(
        conversation_id=conversation_id,
        user_id=user_id,
        role="assistant",
        content=answer or "（AI 未生成有效回答）",
        sources=json.dumps(sources, ensure_ascii=False) if sources else None,
    )
    db.add(msg)
    db.commit()


async def stream_agent_events(task_id: str) -> AsyncGenerator[dict[str, Any], None]:
    """订阅后台任务的事件流。HTTP 断开不影响后台任务。"""
    task_info = _running_tasks.get(task_id)
    if not task_info:
        yield {"event": "_task_done", "data": {}}
        return

    queue: asyncio.Queue = task_info["queue"]
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                if task_info["status"] == "done":
                    break
                continue
            if event.get("event") == "_task_done":
                break
            yield event
    except asyncio.CancelledError:
        logger.info("订阅方断开 task_id=%s，后台任务继续", task_id)
        raise


def get_task_status(task_id: str) -> dict[str, Any]:
    """查询后台任务状态。"""
    task_info = _running_tasks.get(task_id)
    if not task_info:
        return {"status": "unknown", "answer": "", "sources": []}
    return {
        "status": task_info["status"],
        "answer": task_info["answer"],
        "sources": task_info["sources"],
    }