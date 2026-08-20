"""地块管理 API"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import User, FarmLand, CropManagement, FarmWork
from app.schemas import LandCreate, LandUpdate, LandResponse

router = APIRouter(prefix="/api/lands", tags=["地块"])


def _land_summary_fields(db: Session, land_id: int) -> dict:
    """聚合地块卡片需要的额外字段：当前种植作物、最近农事、农事总数。"""
    active_crops = (
        db.query(CropManagement)
        .filter(CropManagement.land_id == land_id, CropManagement.status == "种植中")
        .order_by(CropManagement.created_at.desc())
        .all()
    )
    current_crops = [f"{c.name} · {c.batch_no}" for c in active_crops]

    last_work = (
        db.query(FarmWork)
        .filter(FarmWork.land_id == land_id)
        .order_by(FarmWork.work_date.desc(), FarmWork.created_at.desc())
        .first()
    )
    last_work_str = None
    if last_work:
        last_work_str = f"{last_work.work_type} · {last_work.work_date.strftime('%m-%d')}"

    work_count = db.query(FarmWork).filter(FarmWork.land_id == land_id).count()

    return {
        "current_crops": current_crops,
        "last_work": last_work_str,
        "work_count": work_count,
    }


def _build_land_response(land: FarmLand, db: Session) -> LandResponse:
    """统一构造 LandResponse，包含聚合字段。"""
    crop_count = db.query(CropManagement).filter(
        CropManagement.land_id == land.id,
        CropManagement.status == "种植中"
    ).count()
    summary = _land_summary_fields(db, land.id)
    return LandResponse(
        id=land.id, user_id=land.user_id, name=land.name,
        region=land.region, area=land.area, soil_type=land.soil_type,
        status=land.status, crops=crop_count,
        created_at=land.created_at, updated_at=land.updated_at,
        **summary,
    )


@router.get("", response_model=list[LandResponse])
def list_lands(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取我的地块列表"""
    lands = db.query(FarmLand).filter(FarmLand.user_id == current_user.id).all()
    return [_build_land_response(land, db) for land in lands]


@router.post("", response_model=LandResponse)
def create_land(req: LandCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """创建地块"""
    land = FarmLand(user_id=current_user.id, **req.model_dump())
    db.add(land)
    db.commit()
    db.refresh(land)
    return _build_land_response(land, db)


@router.put("/{land_id}", response_model=LandResponse)
def update_land(land_id: int, req: LandUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """编辑地块"""
    land = db.query(FarmLand).filter(FarmLand.id == land_id, FarmLand.user_id == current_user.id).first()
    if not land:
        raise HTTPException(status_code=404, detail="地块不存在")
    for key, value in req.model_dump(exclude_none=True).items():
        setattr(land, key, value)
    db.commit()
    db.refresh(land)
    return _build_land_response(land, db)


@router.delete("/{land_id}")
def delete_land(land_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """删除地块"""
    land = db.query(FarmLand).filter(FarmLand.id == land_id, FarmLand.user_id == current_user.id).first()
    if not land:
        raise HTTPException(status_code=404, detail="地块不存在")
    # 检查是否有进行中的作物
    active = db.query(CropManagement).filter(
        CropManagement.land_id == land_id, CropManagement.status == "种植中"
    ).first()
    if active:
        raise HTTPException(status_code=400, detail="该地块下有进行中的作物，无法删除")
    db.delete(land)
    db.commit()
    return {"message": "删除成功"}