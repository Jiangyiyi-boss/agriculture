"""农事作业 API"""

import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, FarmLand, CropManagement, FarmWork, ExpertAdvice
from app.schemas import FarmWorkCreate, FarmWorkUpdate, FarmWorkResponse

router = APIRouter(prefix="/api/farm-works", tags=["农事作业"])


@router.get("", response_model=list[FarmWorkResponse])
def list_works(
    work_type: str | None = None,
    batch_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取农事作业列表（可按作业类型、批次过滤）"""
    query = db.query(FarmWork).filter(FarmWork.user_id == current_user.id)
    if work_type and work_type != "全部":
        query = query.filter(FarmWork.work_type == work_type)
    if batch_id:
        query = query.filter(FarmWork.batch_id == batch_id)
    works = query.order_by(FarmWork.work_date.desc()).all()

    return [_format_work(w, db) for w in works]


def _format_work(w: FarmWork, db: Session) -> FarmWorkResponse:
    land = db.query(FarmLand).filter(FarmLand.id == w.land_id).first()
    crop = db.query(CropManagement).filter(CropManagement.id == w.batch_id).first()
    # 农户端：返回该作业所有专家写的建议（含 expert_name），让农户知道是哪个专家写的
    advice_rows = db.query(ExpertAdvice).filter(
        ExpertAdvice.work_id == w.id
    ).order_by(ExpertAdvice.created_at.desc()).all()
    advices = []
    first_advice_content = None
    for a in advice_rows:
        expert = db.query(User).filter(User.id == a.expert_id).first()
        if first_advice_content is None:
            first_advice_content = a.content
        advices.append({
            "expert_id": a.expert_id,
            "expert_name": expert.name if expert else None,
            "content": a.content,
            "is_read": bool(a.is_read),
            "created_at": a.created_at,
        })
    return FarmWorkResponse(
        id=w.id, user_id=w.user_id, land_id=w.land_id, batch_id=w.batch_id,
        work_type=w.work_type, work_date=w.work_date.strftime("%Y-%m-%d") if w.work_date else "",
        land_name=land.name if land else "",
        batch_no=crop.batch_no if crop else "",
        crop_name=crop.name if crop else "",
        crop_variety=crop.variety if crop else None,
        crop_status=crop.status if crop else "",
        plant_date=crop.plant_date.strftime("%Y-%m-%d") if crop and crop.plant_date else None,
        description=w.description, photos=w.photos,
        has_photo=bool(w.photos),
        advice=first_advice_content,
        advices=advices,
        created_at=w.created_at,
    )


@router.post("", response_model=FarmWorkResponse)
def create_work(req: FarmWorkCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """记录农事作业"""
    land = db.query(FarmLand).filter(FarmLand.id == req.land_id, FarmLand.user_id == current_user.id).first()
    if not land:
        raise HTTPException(status_code=404, detail="地块不存在")

    crop = db.query(CropManagement).filter(CropManagement.id == req.batch_id, CropManagement.user_id == current_user.id).first()
    if not crop:
        raise HTTPException(status_code=404, detail="作物批次不存在")

    work = FarmWork(
        user_id=current_user.id,
        land_id=req.land_id,
        batch_id=req.batch_id,
        work_type=req.work_type,
        work_date=datetime.strptime(req.work_date, "%Y-%m-%d"),
        description=req.description,
        photos=req.photos,
    )
    db.add(work)
    db.commit()
    db.refresh(work)
    return _format_work(work, db)


@router.put("/{work_id}", response_model=FarmWorkResponse)
def update_work(work_id: int, req: FarmWorkUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """编辑农事作业"""
    work = db.query(FarmWork).filter(FarmWork.id == work_id, FarmWork.user_id == current_user.id).first()
    if not work:
        raise HTTPException(status_code=404, detail="作业记录不存在")

    update_data = req.model_dump(exclude_none=True)
    if "work_date" in update_data and update_data["work_date"]:
        update_data["work_date"] = datetime.strptime(update_data["work_date"], "%Y-%m-%d")

    for key, value in update_data.items():
        setattr(work, key, value)

    db.commit()
    db.refresh(work)
    return _format_work(work, db)


@router.delete("/{work_id}")
def delete_work(work_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """删除农事作业"""
    work = db.query(FarmWork).filter(FarmWork.id == work_id, FarmWork.user_id == current_user.id).first()
    if not work:
        raise HTTPException(status_code=404, detail="作业记录不存在")
    db.delete(work)
    db.commit()
    return {"message": "删除成功"}


@router.post("/upload")
async def upload_photo(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """上传农事作业照片，落盘到 uploads/farmwork/，返回可访问 URL"""
    allowed = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="图片仅支持 jpg/png/webp")
    ext = (file.filename or "x.jpg").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        ext = "jpg"
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片不能超过10MB")
    filename = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join("uploads", "farmwork", filename)
    with open(path, "wb") as f:
        f.write(data)
    return {"url": f"/uploads/farmwork/{filename}"}