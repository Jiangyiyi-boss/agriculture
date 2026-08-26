"""AI knowledge Q&A APIs — LangGraph ReAct agent."""

from __future__ import annotations

import asyncio
import base64
import json
import os
import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.agents.graph.graph import (
    get_task_status,
    run_agent_background,
    stream_agent_events,
)
from app.agents.graph import graph as graph_module
from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user
from app.core.timezone import now_china
from app.models import AIConversation, AIMessage, User
from app.schemas import AIConversationResponse, AIMessageResponse

router = APIRouter(prefix="/api/ai", tags=["AI 知识问答"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}

AGENT_TYPE = "react"


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _conversation_title(question: str, image_names: list[str]) -> str:
    title = question.strip()[:32] if question.strip() else ""
    return title or (f"图片问题：{image_names[0][:24]}" if image_names else "新的农业问题")


def _get_or_create_conversation(
    db: Session,
    user: User,
    conversation_id: int | None,
    title: str,
) -> AIConversation:
    if conversation_id:
        conversation = db.query(AIConversation).filter(
            AIConversation.id == conversation_id,
            AIConversation.user_id == user.id,
        ).first()
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
        return conversation

    conversation = AIConversation(
        user_id=user.id,
        title=title,
        agent_type=AGENT_TYPE,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


async def _read_images(images: list[UploadFile] | None) -> list[dict[str, Any]]:
    if not images:
        return []
    if len(images) > settings.AI_IMAGE_MAX_COUNT:
        raise HTTPException(status_code=400, detail=f"最多上传 {settings.AI_IMAGE_MAX_COUNT} 张图片")

    payloads: list[dict[str, Any]] = []
    max_bytes = settings.AI_IMAGE_MAX_MB * 1024 * 1024
    for image in images:
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=400, detail="图片仅支持 jpg、jpeg、png、webp")
        data = await image.read()
        if len(data) > max_bytes:
            raise HTTPException(status_code=400, detail=f"单张图片不能超过 {settings.AI_IMAGE_MAX_MB}MB")

        # 持久化保存到 uploads/ai_chat/，便于历史消息回看
        ext_map = {"image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png", "image/webp": "webp"}
        ext = ext_map.get(image.content_type or "", "jpg")
        filename = f"{uuid.uuid4().hex}.{ext}"
        save_path = os.path.join("uploads", "ai_chat", filename)
        with open(save_path, "wb") as f:
            f.write(data)
        image_url = f"/uploads/ai_chat/{filename}"

        payloads.append({
            "base64": base64.b64encode(data).decode("ascii"),
            "mime_type": image.content_type or "",
            "filename": image.filename or "upload-image",
            "size": len(data),
            "url": image_url,
        })
    return payloads


@router.get("/conversations", response_model=list[AIConversationResponse])
def list_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(AIConversation).filter(
        AIConversation.user_id == current_user.id,
    ).order_by(AIConversation.updated_at.desc()).limit(50).all()


@router.get("/conversations/{conversation_id}/messages", response_model=list[AIMessageResponse])
def list_messages(conversation_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = db.query(AIConversation).filter(
        AIConversation.id == conversation_id,
        AIConversation.user_id == current_user.id,
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")
    return db.query(AIMessage).filter(
        AIMessage.conversation_id == conversation_id,
    ).order_by(AIMessage.created_at.asc()).all()


@router.get("/conversations/{conversation_id}/task-status")
def get_conversation_task_status(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
):
    """查询某个会话的后台 agent 任务状态。

    前端用途：用户切页面回到 AI 问答页恢复会话时，调这个接口判断：
    - 若 status=running：后台任务还在跑，前端显示"AI 正在思考..."，
      并轮询这个接口，等任务跑完后刷新消息列表。
    - 若 status=done 或 unknown：任务已结束，直接 GET messages 拉历史即可。
    """
    task_id = f"{current_user.id}:{conversation_id}"
    return get_task_status(task_id)


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conversation = db.query(AIConversation).filter(
        AIConversation.id == conversation_id,
        AIConversation.user_id == current_user.id,
    ).first()
    if not conversation:
        raise HTTPException(status_code=404, detail="对话不存在")

    db.query(AIMessage).filter(AIMessage.conversation_id == conversation_id).delete()
    db.delete(conversation)
    db.commit()

    # 清理 pg 中该会话的 checkpoint（thread_id 按 user_id:conversation_id 隔离）
    if graph_module._pg_saver is not None:
        await graph_module._pg_saver.delete_thread(f"{current_user.id}:{conversation_id}")

    return {"detail": "对话已删除"}


@router.post("/chat/stream")
async def chat_stream(
    message: str = Form(default=""),
    conversation_id: int | None = Form(default=None),
    images: list[UploadFile] | None = File(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    question = message.strip()
    image_payloads = await _read_images(images)
    image_names = [image["filename"] for image in image_payloads]
    image_mimes = [image["mime_type"] for image in image_payloads]
    image_urls = [image["url"] for image in image_payloads]
    image_size = sum(int(image["size"]) for image in image_payloads) if image_payloads else None
    if not question and not image_payloads:
        raise HTTPException(status_code=400, detail="请输入问题或上传图片")

    conversation = _get_or_create_conversation(
        db,
        current_user,
        conversation_id,
        _conversation_title(question, image_names),
    )
    user_message = AIMessage(
        conversation_id=conversation.id,
        user_id=current_user.id,
        role="user",
        content=question or "请帮我识别这张农业图片",
        image_name=",".join(image_names) if image_names else None,
        image_mime=",".join(image_mimes) if image_mimes else None,
        image_size=image_size,
        image_urls=",".join(image_urls) if image_urls else None,
    )
    conversation.updated_at = now_china()
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    async def generate():
        answer = ""
        sources: list[dict] = []
        yield _sse("meta", {
            "conversation_id": conversation.id,
            "conversation_title": conversation.title,
            "user_message_id": user_message.id,
            "agent_type": AGENT_TYPE,
        })
        try:
            # 正常流式：用户在页面看 AI 边想边打字
            async for event in run_agent_stream(
                db=db,
                user=current_user,
                conversation_id=conversation.id,
                question=question,
                images=image_payloads,
            ):
                evt = event.get("event", "")
                data = event.get("data", {})
                if evt == "status":
                    yield _sse("status", data)
                elif evt == "chunk":
                    answer += data.get("content", "")
                    yield _sse("chunk", data)
                elif evt == "done":
                    answer = data.get("answer", answer)
                    sources = data.get("sources", [])
                elif evt == "error":
                    raise RuntimeError(data.get("detail", "AI 问答暂时不可用"))

            # 流式正常完成：落库 AIMessage
            assistant_message = AIMessage(
                conversation_id=conversation.id,
                user_id=current_user.id,
                role="assistant",
                content=answer,
                sources=json.dumps(sources, ensure_ascii=False) if sources else None,
            )
            conversation.updated_at = now_china()
            db.add(assistant_message)
            db.commit()
            db.refresh(assistant_message)

            yield _sse("done", {
                "message_id": assistant_message.id,
                "agent_type": AGENT_TYPE,
                "sources": sources,
            })
        except asyncio.CancelledError:
            # HTTP 断开（用户切页面）：启动后台 ainvoke 跑完落库
            # 用独立 db session，不受 HTTP 生命周期影响
            try:
                db.rollback()
            except Exception:
                pass
            background_db = SessionLocal()
            try:
                await run_agent_background(
                    db=background_db,
                    user=current_user,
                    conversation_id=conversation.id,
                    question=question,
                    images=image_payloads,
                    user_message_id=user_message.id,
                )
            except Exception:
                background_db.close()
            # 不 re-raise，让协程正常结束（不抛错给 uvicorn）
            return
        except Exception as error:
            detail = str(error) or "AI 问答暂时不可用"
            # 流式途中出错也落库一条错误消息
            try:
                assistant_message = AIMessage(
                    conversation_id=conversation.id,
                    user_id=current_user.id,
                    role="assistant",
                    content=f"抱歉，{detail}",
                )
                db.add(assistant_message)
                db.commit()
            except Exception:
                db.rollback()
            yield _sse("error", {"detail": detail})

    return StreamingResponse(generate(), media_type="text/event-stream")