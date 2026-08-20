"""推送相关 API"""

from datetime import datetime

from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.core.timezone import now_china
from app.models import User, Notification

router = APIRouter(prefix="/api/push", tags=["推送"])


@router.get("/latest")
def get_latest_push(
    current_user: User = Depends(get_current_user),
):
    """返回当前用户未弹出的推送通知（供前端浏览器通知弹窗）。

    返回所有未读的推送类通知（solar_term / weather_alert），
    不限今天——之前漏弹的也会补弹。前端弹窗后调用 mark-shown 标记已读。
    """
    from sqlalchemy import func
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        notifications = (
            db.query(Notification)
            .filter(
                Notification.user_id == current_user.id,
                Notification.is_read == False,
                Notification.type.in_(["solar_term", "weather_alert"]),
            )
            .order_by(Notification.created_at.desc())
            .limit(5)
            .all()
        )
        return [
            {
                "id": n.id,
                "type": n.type,
                "title": n.title,
                "content": n.content,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifications
        ]
    finally:
        db.close()


@router.post("/mark-shown/{notification_id}")
def mark_push_shown(
    notification_id: int,
    current_user: User = Depends(get_current_user),
):
    """标记推送通知已弹出（设为已读），避免重复弹窗。"""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        n = (
            db.query(Notification)
            .filter(
                Notification.id == notification_id,
                Notification.user_id == current_user.id,
            )
            .first()
        )
        if n:
            n.is_read = True
            db.commit()
        return {"message": "ok"}
    finally:
        db.close()
