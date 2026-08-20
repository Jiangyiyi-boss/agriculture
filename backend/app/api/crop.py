"""作物管理 API"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.timezone import now_china
from app.models import User, FarmLand, CropManagement, FarmWork, ExpertAdvice
from app.schemas import CropCreate, CropUpdate, CropResponse


def _crop_summary_fields(db: Session, crop_id: int) -> dict:
    """聚合作物列表/首页需要的额外字段：作业数、专家建议数、最近一次作业。"""
    # 采收已独立为按钮操作，不再算作农事作业，统计时排除"采收"类型的历史记录
    last_work = (
        db.query(FarmWork)
        .filter(FarmWork.batch_id == crop_id, FarmWork.work_type != "采收")
        .order_by(FarmWork.work_date.desc(), FarmWork.created_at.desc())
        .first()
    )
    last_work_str = None
    if last_work:
        last_work_str = f"{last_work.work_type} · {last_work.work_date.strftime('%m-%d')}"

    work_count = db.query(FarmWork).filter(
        FarmWork.batch_id == crop_id, FarmWork.work_type != "采收"
    ).count()
    # 只统计未读的专家建议数（农户查看后标记已读，标签自动消失）
    advice_count = (
        db.query(ExpertAdvice)
        .join(FarmWork, ExpertAdvice.work_id == FarmWork.id)
        .filter(FarmWork.batch_id == crop_id, ExpertAdvice.is_read == False)
        .count()
    )
    return {
        "work_count": work_count,
        "advice_count": advice_count,
        "last_work": last_work_str,
    }


def _build_crop_response(c: CropManagement, land_name: str, db: Session) -> CropResponse:
    """统一构造 CropResponse，包含聚合字段。"""
    summary = _crop_summary_fields(db, c.id)
    return CropResponse(
        id=c.id,
        user_id=c.user_id,
        land_id=c.land_id,
        batch_no=c.batch_no,
        name=c.name,
        variety=c.variety,
        land_name=land_name,
        plant_date=c.plant_date.strftime("%Y-%m-%d") if c.plant_date else "",
        status=c.status,
        harvest_date=c.harvest_date.strftime("%Y-%m-%d") if c.harvest_date else None,
        created_at=c.created_at,
        **summary,
    )

router = APIRouter(prefix="/api/crops", tags=["作物"])


def generate_batch_no(db: Session) -> str:
    """生成批次号: NY + YYYYMMDD + 3位序号"""
    today = now_china().strftime("%Y%m%d")
    prefix = f"NY{today}"
    count = db.query(CropManagement).filter(CropManagement.batch_no.like(f"{prefix}%")).count()
    return f"{prefix}{count + 1:03d}"


@router.get("", response_model=list[CropResponse])
def list_crops(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取我的作物列表（progress/stage 实时计算，并附带聚合统计）"""
    crops = db.query(CropManagement).filter(CropManagement.user_id == current_user.id).order_by(CropManagement.created_at.desc()).all()
    result = []
    for c in crops:
        land = db.query(FarmLand).filter(FarmLand.id == c.land_id).first()
        result.append(_build_crop_response(c, land.name if land else "", db))
    return result


@router.post("", response_model=CropResponse)
def create_crop(req: CropCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """创建作物（自动生成批次号）"""
    land = db.query(FarmLand).filter(FarmLand.id == req.land_id, FarmLand.user_id == current_user.id).first()
    if not land:
        raise HTTPException(status_code=404, detail="地块不存在")

    batch_no = generate_batch_no(db)
    crop = CropManagement(
        user_id=current_user.id,
        land_id=req.land_id,
        batch_no=batch_no,
        name=req.name,
        variety=req.variety,
        plant_date=datetime.strptime(req.plant_date, "%Y-%m-%d") if req.plant_date else None,
        status="种植中",
    )
    db.add(crop)

    # 地块状态更新
    land.status = "种植中"
    db.commit()
    db.refresh(crop)

    # 返回时实时计算 progress/stage 和聚合字段
    return _build_crop_response(crop, land.name, db)


@router.put("/{crop_id}", response_model=CropResponse)
def update_crop(crop_id: int, req: CropUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """编辑作物"""
    crop = db.query(CropManagement).filter(CropManagement.id == crop_id, CropManagement.user_id == current_user.id).first()
    if not crop:
        raise HTTPException(status_code=404, detail="作物不存在")

    update_data = req.model_dump(exclude_none=True)
    if "plant_date" in update_data and update_data["plant_date"]:
        update_data["plant_date"] = datetime.strptime(update_data["plant_date"], "%Y-%m-%d")

    for key, value in update_data.items():
        setattr(crop, key, value)

    # 如果采收，更新地块状态
    if update_data.get("status") == "已采收":
        land = db.query(FarmLand).filter(FarmLand.id == crop.land_id).first()
        if land:
            active = db.query(CropManagement).filter(
                CropManagement.land_id == land.id,
                CropManagement.id != crop.id,
                CropManagement.status == "种植中"
            ).first()
            if not active:
                land.status = "空闲"

    db.commit()
    db.refresh(crop)

    land = db.query(FarmLand).filter(FarmLand.id == crop.land_id).first()
    # 返回时实时计算 progress/stage 和聚合字段（避免数据库里的过期值）
    return _build_crop_response(crop, land.name if land else "", db)


@router.delete("/{crop_id}")
def delete_crop(crop_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """删除作物"""
    crop = db.query(CropManagement).filter(CropManagement.id == crop_id, CropManagement.user_id == current_user.id).first()
    if not crop:
        raise HTTPException(status_code=404, detail="作物不存在")
    db.delete(crop)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{crop_id}/harvest")
def harvest_crop(crop_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """采收作物：状态改为已采收，记录采收日期，地块状态回收。

    采收是独立操作（不走农事作业），采收后：
    - 作物状态 → 已采收
    - harvest_date 记录实际采收日期
    - 若该地块无其他种植中作物 → 地块状态变回空闲
    """
    crop = db.query(CropManagement).filter(
        CropManagement.id == crop_id,
        CropManagement.user_id == current_user.id,
    ).first()
    if not crop:
        raise HTTPException(status_code=404, detail="作物不存在")
    if crop.status == "已采收":
        raise HTTPException(status_code=400, detail="该作物已采收")

    crop.status = "已采收"
    crop.harvest_date = now_china()

    # 地块状态回收：该地块没有其他种植中作物时，地块变空闲
    land = db.query(FarmLand).filter(FarmLand.id == crop.land_id).first()
    if land:
        active = db.query(CropManagement).filter(
            CropManagement.land_id == land.id,
            CropManagement.id != crop.id,
            CropManagement.status == "种植中",
        ).first()
        if not active:
            land.status = "空闲"

    db.commit()
    return {"message": "采收成功", "harvest_date": crop.harvest_date.strftime("%Y-%m-%d")}


@router.post("/{crop_id}/restore")
def restore_crop(crop_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """恢复种植中：已采收的作物恢复为种植中状态（误采收或需要重新记录时使用）。"""
    crop = db.query(CropManagement).filter(
        CropManagement.id == crop_id,
        CropManagement.user_id == current_user.id,
    ).first()
    if not crop:
        raise HTTPException(status_code=404, detail="作物不存在")
    if crop.status != "已采收":
        raise HTTPException(status_code=400, detail="该作物不是已采收状态")

    crop.status = "种植中"
    crop.harvest_date = None

    # 地块状态恢复为种植中
    land = db.query(FarmLand).filter(FarmLand.id == crop.land_id).first()
    if land:
        land.status = "种植中"

    db.commit()
    return {"message": "已恢复种植中"}


@router.post("/{crop_id}/mark-advice-read")
def mark_advice_read(crop_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """农户查看作物详情时，将该作物的所有专家建议标记为已读。"""
    crop = db.query(CropManagement).filter(
        CropManagement.id == crop_id,
        CropManagement.user_id == current_user.id,
    ).first()
    if not crop:
        raise HTTPException(status_code=404, detail="作物不存在")

    # 先查出该作物下所有未读建议的 work_id，再批量更新（避免 join+update 的兼容性问题）
    work_ids = [r[0] for r in db.query(FarmWork.id).filter(FarmWork.batch_id == crop_id).all()]
    if not work_ids:
        return {"message": "无作业记录"}

    unread_advices = db.query(ExpertAdvice).filter(
        ExpertAdvice.work_id.in_(work_ids),
        ExpertAdvice.is_read == False,
    ).all()

    for advice in unread_advices:
        advice.is_read = True

    db.commit()
    return {"message": f"已标记 {len(unread_advices)} 条建议为已读"}