"""用户相关 API"""

import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.security import get_current_user
from app.models import User
from app.schemas import UserResponse, UserUpdateRequest, UserLocationUpdate

router = APIRouter(prefix="/api/users", tags=["用户"])


@router.put("/me", response_model=UserResponse)
def update_profile(req: UserUpdateRequest, current_user: User = Depends(get_current_user)):
    """更新个人资料

    权限规则：
    - 农户(role=1)：可改 name/avatar/region/bio
    - 专家(role=2)：可改 name/avatar/bio，**不可改 title/specialty**（由管理员维护）
    - 管理员(role=3)：可改全部字段
    """
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        updates = req.model_dump(exclude_none=True)

        # 专家不能修改职称和专业领域，由管理员维护
        if current_user.role == 2:
            updates.pop("title", None)
            updates.pop("specialty", None)

        for key, value in updates.items():
            setattr(user, key, value)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()


@router.post("/avatar")
async def upload_avatar(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """上传用户头像，落盘到 uploads/avatar/，返回可访问 URL"""
    allowed = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="图片仅支持 jpg/png/webp")
    ext = (file.filename or "x.jpg").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        ext = "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join("uploads", "avatar", filename)
    data = await file.read()
    if len(data) > 3 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="头像图片不能超过3MB")
    with open(path, "wb") as f:
        f.write(data)
    return {"url": f"/uploads/avatar/{filename}"}


@router.post("/update-location")
def update_location(
    req: UserLocationUpdate,
    current_user: User = Depends(get_current_user),
):
    """更新用户地理位置（天气推送用）"""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        # 位置没变化则跳过写入
        if user.adcode == req.adcode and user.city == req.city:
            return {"message": "位置未变化，跳过更新"}
        user.adcode = req.adcode
        user.city = req.city
        user.adcode_updated_at = datetime.now(timezone.utc)
        db.commit()
        return {"message": "位置已更新", "adcode": req.adcode, "city": req.city}
    finally:
        db.close()
