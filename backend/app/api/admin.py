"""管理员后台 API"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import get_current_user, hash_password
from app.core.timezone import now_china
from app.models import User, FarmLand, Article, ExpertQuestion, FarmWork
from app.schemas import (
    AdminUserUpdate, AdminExpertCreate, AdminExpertUpdate,
    UserResponse, ArticleResponse, ArticleReviewRequest,
)

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


def check_admin(user: User):
    if user.role != 3:
        raise HTTPException(status_code=403, detail="仅管理员可操作")


# ========== 数据看板 ==========
@router.get("/stats")
def get_stats(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取平台统计数据"""
    check_admin(current_user)
    return {
        "users": db.query(User).filter(User.role == 1).count(),
        "experts": db.query(User).filter(User.role == 2).count(),
        "articles": db.query(Article).filter(Article.review_status == "published").count(),
        "pending_articles": db.query(Article).filter(Article.review_status == "pending", Article.author_role == 2).count(),
        "total_consultations": db.query(ExpertQuestion).count(),
        "land_plots": db.query(FarmLand).count(),
    }


# ========== 用户管理 ==========
@router.get("/users", response_model=list[UserResponse])
def list_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取所有用户"""
    check_admin(current_user)
    users = db.query(User).order_by(User.created_at.desc()).limit(100).all()
    return users


@router.put("/users/{user_id}")
def update_user(user_id: int, req: AdminUserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """管理用户（启用/禁用）"""
    check_admin(current_user)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    for key, value in req.model_dump(exclude_none=True).items():
        setattr(user, key, value)
    db.commit()
    return {"message": "更新成功"}


# ========== 专家管理 ==========
@router.post("/experts", response_model=UserResponse)
def create_expert(req: AdminExpertCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """创建专家账号"""
    check_admin(current_user)
    if db.query(User).filter(User.phone == req.phone).first():
        raise HTTPException(status_code=400, detail="手机号已存在")

    expert = User(
        phone=req.phone,
        password_hash=hash_password(req.password),
        name=req.name,
        role=2,
        specialty=req.specialty,
        title=req.title,
        bio=req.bio,
        status=1,
        must_change_password=True,  # 管理员创建的专家账号必须首次登录后改密码
    )
    db.add(expert)
    db.commit()
    db.refresh(expert)
    return expert


@router.get("/experts", response_model=list[UserResponse])
def list_experts_admin(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取专家列表"""
    check_admin(current_user)
    return db.query(User).filter(User.role == 2).all()


@router.delete("/experts/{expert_id}")
def delete_expert(expert_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """删除专家"""
    check_admin(current_user)
    expert = db.query(User).filter(User.id == expert_id, User.role == 2).first()
    if not expert:
        raise HTTPException(status_code=404, detail="专家不存在")
    db.delete(expert)
    db.commit()
    return {"message": "删除成功"}


# ========== 月度趋势数据 ==========
@router.get("/monthly-data")
def get_monthly_data(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取近6个月农户新增数据（仅 role=1，按月统计当月新增）"""
    check_admin(current_user)
    now = now_china()
    months = []
    for i in range(5, -1, -1):
        month_start = (now.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
        month_end = (month_start.replace(month=month_start.month % 12 + 1, day=1) if month_start.month < 12 else month_start.replace(year=month_start.year + 1, month=1, day=1))
        if month_end <= month_start:
            month_end = month_start + timedelta(days=31)
        count = db.query(User).filter(
            User.role == 1,
            User.created_at >= month_start,
            User.created_at < month_end,
        ).count()
        months.append({"month": month_start.strftime("%m月"), "users": count})
    return months


# ========== 专家管理 - 更新 ==========
@router.put("/experts/{expert_id}", response_model=UserResponse)
def update_expert(expert_id: int, req: AdminExpertUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """编辑专家资料（姓名/职称/专业领域/简介/状态）"""
    check_admin(current_user)
    expert = db.query(User).filter(User.id == expert_id, User.role == 2).first()
    if not expert:
        raise HTTPException(status_code=404, detail="专家不存在")
    for key, value in req.model_dump(exclude_none=True).items():
        setattr(expert, key, value)
    db.commit()
    db.refresh(expert)
    return expert


# ========== 文章审核管理 ==========
def _format_article_admin(a: Article, db: Session) -> ArticleResponse:
    """管理员视角的文章格式化（含作者信息）"""
    author = db.query(User).filter(User.id == a.author_id).first()
    return ArticleResponse(
        id=a.id, author_id=a.author_id,
        author_name=author.name if author else "",
        author_role=author.role if author else None,
        title=a.title, category=a.category,
        content=a.content, summary=a.summary, cover=a.cover,
        source=a.source,
        review_status=a.review_status,
        review_reason=a.review_reason,
        published_at=a.published_at,
        date=a.created_at.strftime("%Y-%m-%d") if a.created_at else "",
        created_at=a.created_at,
    )


@router.get("/articles", response_model=list[ArticleResponse])
def list_articles_admin(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取全部文章（含待审核/已发布/已拒绝），供管理员审核台使用"""
    check_admin(current_user)
    articles = db.query(Article).order_by(Article.created_at.desc()).limit(200).all()
    return [_format_article_admin(a, db) for a in articles]


@router.post("/articles/{article_id}/review", response_model=ArticleResponse)
def review_article(article_id: int, req: ArticleReviewRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """审核专家投稿：approve=通过并发布；reject=拒绝（可附理由）"""
    check_admin(current_user)
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.review_status != "pending":
        raise HTTPException(status_code=400, detail="该文章已审核，无法重复审核")

    now = now_china()
    article.reviewed_by = current_user.id
    article.reviewed_at = now
    if req.action == "approve":
        article.review_status = "published"
        article.published_at = now
        article.review_reason = None
    else:
        article.review_status = "rejected"
        article.review_reason = req.reason or "内容不符合要求"
        # 拒绝后撤回发布时间
        article.published_at = None

    db.commit()
    db.refresh(article)
    return _format_article_admin(article, db)