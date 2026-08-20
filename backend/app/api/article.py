"""三农资讯 API"""

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.timezone import now_china
from app.models import User, Article, ArticleView
from app.schemas import ArticleCreate, ArticleUpdate, ArticleResponse

router = APIRouter(prefix="/api/articles", tags=["三农资讯"])


@router.get("", response_model=list[ArticleResponse])
def list_articles(category: str | None = None, db: Session = Depends(get_db)):
    """获取文章列表"""
    query = db.query(Article).filter(Article.review_status == "published")
    if category and category != "全部":
        query = query.filter(Article.category == category)
    articles = query.order_by(Article.created_at.desc()).limit(20).all()
    return [_format_article(a, db) for a in articles]


@router.get("/by-category", response_model=dict)
def list_articles_by_category(db: Session = Depends(get_db)):
    """按分类分组返回最新3篇已发布文章（农户端三农资讯页使用）"""
    categories = ["政策解读", "种植技术", "病虫害防治", "市场行情", "平台公告"]
    result = {}
    for cat in categories:
        articles = (
            db.query(Article)
            .filter(Article.category == cat, Article.review_status == "published")
            .order_by(Article.created_at.desc())
            .limit(3)
            .all()
        )
        if articles:
            result[cat] = [_format_article(a, db) for a in articles]
    return result


@router.get("/category/{category}", response_model=list[ArticleResponse])
def list_articles_in_category(category: str, db: Session = Depends(get_db)):
    """获取某分类的所有已发布文章（分类列表页使用）"""
    articles = (
        db.query(Article)
        .filter(Article.category == category, Article.review_status == "published")
        .order_by(Article.created_at.desc())
        .all()
    )
    return [_format_article(a, db) for a in articles]


@router.get("/mine", response_model=list[ArticleResponse])
def list_my_articles(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前用户（专家/管理员）自己的全部文章（含待审核/已拒绝）"""
    if current_user.role not in (2, 3):
        raise HTTPException(status_code=403, detail="无权限")
    articles = (
        db.query(Article)
        .filter(Article.author_id == current_user.id)
        .order_by(Article.created_at.desc())
        .all()
    )
    return [_format_article(a, db) for a in articles]


def _format_article(a: Article, db: Session) -> ArticleResponse:
    author = db.query(User).filter(User.id == a.author_id).first()
    return ArticleResponse(
        id=a.id, author_id=a.author_id,
        author_name=author.name if author else "",
        author_role=author.role if author else None,
        title=a.title, category=a.category,
        content=a.content, summary=a.summary, cover=a.cover,
        source=a.source, original_author=a.original_author,
        review_status=a.review_status,
        review_reason=a.review_reason,
        published_at=a.published_at,
        date=a.created_at.strftime("%Y-%m-%d") if a.created_at else "",
        created_at=a.created_at,
    )


@router.get("/my-views", response_model=list[dict])
def list_my_views(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取当前用户的文章浏览历史（最近20条）"""
    views = (
        db.query(ArticleView)
        .filter(ArticleView.user_id == current_user.id)
        .order_by(ArticleView.viewed_at.desc())
        .limit(20)
        .all()
    )
    result = []
    for v in views:
        article = db.query(Article).filter(Article.id == v.article_id).first()
        if not article:
            continue
        result.append({
            "article_id": article.id,
            "title": article.title,
            "category": article.category,
            "cover": article.cover,
            "viewed_at": v.viewed_at.strftime("%Y-%m-%d %H:%M") if v.viewed_at else "",
        })
    return result


@router.post("/{article_id}/view")
def record_article_view(article_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """记录文章浏览（同一用户重复浏览只更新时间）"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    view = (
        db.query(ArticleView)
        .filter(ArticleView.user_id == current_user.id, ArticleView.article_id == article_id)
        .first()
    )
    if view:
        view.viewed_at = now_china()
    else:
        db.add(ArticleView(user_id=current_user.id, article_id=article_id, viewed_at=now_china()))
    db.commit()
    return {"message": "已记录"}


@router.get("/{article_id}", response_model=ArticleResponse)
def get_article(article_id: int, db: Session = Depends(get_db)):
    """获取文章详情"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    return _format_article(article, db)


@router.post("", response_model=ArticleResponse)
def create_article(req: ArticleCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """发布文章（专家/管理员）

    专家(role=2)投稿进入待审核；管理员(role=3)发布直接上线。
    """
    if current_user.role not in (2, 3):
        raise HTTPException(status_code=403, detail="无权限")

    now = now_china()
    if current_user.role == 3:
        # 管理员发文直接发布
        article = Article(
            author_id=current_user.id, **req.model_dump(),
            review_status="published", published_at=now,
        )
    else:
        # 专家投稿进入待审核
        article = Article(
            author_id=current_user.id, **req.model_dump(),
            review_status="pending",
        )
    db.add(article)
    db.commit()
    db.refresh(article)
    return _format_article(article, db)


@router.put("/{article_id}", response_model=ArticleResponse)
def update_article(article_id: int, req: ArticleUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """编辑文章

    专家编辑被拒绝的文章后重新提交审核；已发布的文章编辑后直接生效（不重新审核）。
    管理员编辑自己的文章保持已发布。
    """
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.author_id != current_user.id and current_user.role != 3:
        raise HTTPException(status_code=403, detail="只能编辑自己的文章")

    for key, value in req.model_dump(exclude_none=True).items():
        setattr(article, key, value)

    # 专家编辑：被拒绝的文章重新提交审核；已发布的直接生效（不重新审核）
    if current_user.role == 2:
        if article.review_status == "rejected":
            article.review_status = "pending"
            article.review_reason = None
            article.reviewed_by = None
            article.reviewed_at = None
        # published 状态保持不变，直接生效

    db.commit()
    db.refresh(article)
    return _format_article(article, db)


@router.delete("/{article_id}")
def delete_article(article_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """删除文章"""
    article = db.query(Article).filter(Article.id == article_id).first()
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    if article.author_id != current_user.id and current_user.role != 3:
        raise HTTPException(status_code=403, detail="只能删除自己的文章")

    db.delete(article)
    db.commit()
    return {"message": "删除成功"}


@router.post("/upload")
async def upload_article_image(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """上传文章正文配图（专家/管理员）"""
    if current_user.role not in (2, 3):
        raise HTTPException(status_code=403, detail="无权限")

    # 校验文件类型
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="仅支持 JPG/PNG/WebP/GIF 图片")

    # 限制 5MB
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片大小不能超过 5MB")

    # 保存文件
    ext = os.path.splitext(file.filename or "")[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    upload_dir = os.path.join("uploads", "articles")
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(content)

    return {"url": f"/uploads/articles/{filename}"}