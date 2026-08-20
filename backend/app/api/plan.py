"""农事计划 API（首页"今日农事"卡片）"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.timezone import now_china
from app.models import User, FarmPlan
from app.schemas import FarmPlanCreate, FarmPlanUpdate, FarmPlanResponse

router = APIRouter(prefix="/api/plans", tags=["农事计划"])


def _to_response(p: FarmPlan) -> FarmPlanResponse:
    return FarmPlanResponse(
        id=p.id,
        content=p.content,
        plan_date=p.plan_date.strftime("%Y-%m-%d") if p.plan_date else "",
        is_done=bool(p.is_done),
        done_at=p.done_at,
        created_at=p.created_at,
    )


@router.get("", response_model=list[FarmPlanResponse])
def list_plans(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前用户全部农事计划。

    排序：未完成在前，同状态按计划日期、id 升序。
    前端首页卡片取未完成的展示，"查看全部"弹窗展示全部。
    """
    plans = (
        db.query(FarmPlan)
        .filter(FarmPlan.user_id == current_user.id)
        .order_by(FarmPlan.is_done.asc(), FarmPlan.plan_date.asc(), FarmPlan.id.asc())
        .all()
    )
    return [_to_response(p) for p in plans]


@router.post("", response_model=FarmPlanResponse)
def create_plan(req: FarmPlanCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """新增农事计划（plan_date 缺省为今天）"""
    if req.plan_date:
        try:
            plan_date = datetime.strptime(req.plan_date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="计划日期格式错误，应为 YYYY-MM-DD")
    else:
        plan_date = now_china().replace(hour=0, minute=0, second=0, microsecond=0)

    plan = FarmPlan(user_id=current_user.id, content=req.content.strip(), plan_date=plan_date)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return _to_response(plan)


@router.patch("/{plan_id}", response_model=FarmPlanResponse)
def update_plan(
    plan_id: int,
    req: FarmPlanUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """切换计划完成状态"""
    plan = db.query(FarmPlan).filter(FarmPlan.id == plan_id, FarmPlan.user_id == current_user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")

    plan.is_done = req.is_done
    plan.done_at = now_china() if req.is_done else None
    db.commit()
    db.refresh(plan)
    return _to_response(plan)


@router.delete("/{plan_id}")
def delete_plan(plan_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """删除农事计划"""
    plan = db.query(FarmPlan).filter(FarmPlan.id == plan_id, FarmPlan.user_id == current_user.id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="计划不存在")

    db.delete(plan)
    db.commit()
    return {"message": "已删除"}
