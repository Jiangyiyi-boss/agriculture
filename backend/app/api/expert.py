"""专家工作台 API（含 IM 即时通讯式咨询）"""

import os
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.timezone import now_china, CHINA_TZ
from app.models import (
    User, FarmWork, FarmLand, CropManagement, ExpertAdvice,
    ExpertQuestion, ExpertAnswer, ExpertMessage, Notification,
)
from app.schemas import (
    ExpertAdviceCreate, ExpertAnswerCreate,
    ExpertQuestionResponse, FarmWorkResponse,
    ExpertConsultationStart, ExpertMessageCreate, ExpertMessageResponse,
    ExpertConsultationResponse, ExpertRateCreate,
)

router = APIRouter(prefix="/api/expert", tags=["专家工作台"])

# 专家结束会话时自动发送的预设结束语
DEFAULT_EXPERT_CLOSING = "本次会话已结束。如有新问题请发起新咨询。"

# 专家可见农户作业的咨询时效（天）：只看近 N 天内咨询过自己的农户的作业，
# 避免历史咨询累积导致可见农户无限增长。
EXPERT_WORK_VISIBILITY_DAYS = 30


def check_expert(user: User):
    if user.role not in (2, 3):
        raise HTTPException(status_code=403, detail="仅专家和管理员可操作")


def _get_visible_farmer_ids(current_user: User, db: Session) -> list[int] | None:
    """返回当前专家可见的农户 user_id 列表。

    - 专家（role=2）：只能看近 EXPERT_WORK_VISIBILITY_DAYS 天内咨询过自己的农户
      （咨询关系 + 时效，避免可见农户无限累积）
    - 管理员（role=3）：返回 None 表示不受限（可看所有农户）

    用于 list_all_works / create_advice / my_farmers 共享同一套可见范围逻辑。
    """
    if current_user.role == 3:
        return None  # 管理员不受限
    cutoff = now_china() - timedelta(days=EXPERT_WORK_VISIBILITY_DAYS)
    return [
        uid for (uid,) in db.query(ExpertQuestion.user_id).filter(
            ExpertQuestion.expert_id == current_user.id,
            ExpertQuestion.updated_at >= cutoff,
        ).distinct().all()
    ]


def _assert_can_access_work(work: FarmWork, current_user: User, db: Session) -> None:
    """校验当前用户是否有权访问某条农事作业（用于写指导建议等写操作）。

    - 管理员：直接通过
    - 专家：仅当该作业属于"近 N 天咨询过自己的农户"时通过
    """
    if current_user.role == 3:
        return
    visible_ids = _get_visible_farmer_ids(current_user, db)
    if visible_ids is None or work.user_id not in visible_ids:
        raise HTTPException(
            status_code=403,
            detail=f"该作业属于未与你近期建立咨询关系的农户，无法查看或建议",
        )


def _is_party(q: ExpertQuestion, user: User) -> tuple[bool, bool]:
    """返回 (is_farmer, is_expert)。"""
    is_farmer = (q.user_id == user.id)
    is_expert = (q.expert_id == user.id) and (user.role in (2, 3))
    return is_farmer, is_expert


def _to_consultation(q: ExpertQuestion, farmer_name: str, db: Session) -> ExpertConsultationResponse:
    expert = db.query(User).filter(User.id == q.expert_id).first() if q.expert_id else None
    farmer = db.query(User).filter(User.id == q.user_id).first() if q.user_id else None
    unread = db.query(Notification).filter(
        Notification.user_id == q.user_id,
        Notification.question_id == q.id,
        Notification.is_read == False,
    ).count() if q.id else 0

    # 专家端软提示：会话进行中且最后一条消息是专家发的且距当前 >= 15 分钟
    # 农户未回复时，前端会话栏显示"农户已 N 分钟未回复"
    farmer_idle_minutes = None
    if q.status == "进行中" and q.id:
        last_msg = db.query(ExpertMessage).filter(
            ExpertMessage.question_id == q.id
        ).order_by(ExpertMessage.id.desc()).first()
        if last_msg and last_msg.sender_role == "expert" and last_msg.created_at:
            delta_seconds = (now_china() - last_msg.created_at).total_seconds()
            if delta_seconds >= 15 * 60:
                farmer_idle_minutes = int(delta_seconds // 60)

    return ExpertConsultationResponse(
        id=q.id, expert_id=q.expert_id,
        expert_name=expert.name if expert else None,
        expert_avatar=expert.avatar if expert else None,
        expert_title=expert.title if expert else None,
        expert_specialty=expert.specialty if expert else None,
        farmer_id=q.user_id, farmer_name=farmer_name or "",
        farmer_avatar=farmer.avatar if farmer else None,
        title=q.title, last_preview=q.description,
        status=q.status, rating=q.rating,
        rating_skipped_at=q.rating_skipped_at,
        unread_count=unread,
        ended_at=q.ended_at, ended_by=q.ended_by,
        farmer_idle_minutes=farmer_idle_minutes,
        created_at=q.created_at or now_china(),
        updated_at=q.updated_at,
    )


# ========== 农事作业管理 ==========
@router.get("/works", response_model=list[FarmWorkResponse])
def list_all_works(
    farmer_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查看农户作业记录

    隐私策略：
    - 专家（role=2）：只能查看近 EXPERT_WORK_VISIBILITY_DAYS 天内咨询过自己的农户的作业
    - 管理员（role=3）：可查看所有农户作业（监督职责）
    可选 farmer_id 参数筛选特定农户的作业。
    """
    check_expert(current_user)

    query = db.query(FarmWork)

    # 专家受"咨询关系 + 30 天时效"限制；管理员不受限
    visible_ids = _get_visible_farmer_ids(current_user, db)
    if visible_ids is not None:
        if not visible_ids:
            return []
        query = query.filter(FarmWork.user_id.in_(visible_ids))

    # 可选：按农户筛选
    if farmer_id:
        # 二次校验：专家不能通过 farmer_id 越权查看不在可见范围内的农户
        if visible_ids is not None and farmer_id not in visible_ids:
            raise HTTPException(status_code=403, detail="无权查看该农户作业")
        query = query.filter(FarmWork.user_id == farmer_id)

    works = query.order_by(FarmWork.work_date.desc()).limit(50).all()
    result = []
    is_expert_role = current_user.role == 2
    for w in works:
        land = db.query(FarmLand).filter(FarmLand.id == w.land_id).first()
        crop = db.query(CropManagement).filter(CropManagement.id == w.batch_id).first()
        # 已采收作物的作业不出现在专家端指导列表（农户已收完，专家无需再指导）
        if crop and crop.status == "已采收":
            continue
        # 专家只看自己写的建议（防越权：别的专家写的建议当前专家看不到）
        # 管理员（role=3）可看所有专家的建议用于监督
        advice_query = db.query(ExpertAdvice).filter(ExpertAdvice.work_id == w.id)
        if is_expert_role:
            advice_query = advice_query.filter(ExpertAdvice.expert_id == current_user.id)
        advice = advice_query.first()
        farmer = db.query(User).filter(User.id == w.user_id).first()
        result.append(FarmWorkResponse(
            id=w.id, user_id=w.user_id, land_id=w.land_id, batch_id=w.batch_id,
            work_type=w.work_type, work_date=w.work_date.strftime("%Y-%m-%d") if w.work_date else "",
            land_name=land.name if land else "",
            batch_no=crop.batch_no if crop else "",
            description=w.description, photos=w.photos,
            has_photo=bool(w.photos),
            advice=advice.content if advice else None,
            farmer_name=farmer.name if farmer else "",
            farmer_phone=f"{farmer.phone[:3]}****{farmer.phone[-4:]}" if farmer else "",
            crop_name=crop.name if crop else "",
            crop_variety=crop.variety if crop else None,
            crop_status=crop.status if crop else "",
            plant_date=crop.plant_date.strftime("%Y-%m-%d") if crop and crop.plant_date else None,
            created_at=w.created_at,
        ))
    return result


@router.post("/advice")
def create_advice(req: ExpertAdviceCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """写专家建议

    权限校验：专家只能给"近 N 天咨询过自己的农户"的作业写建议，避免越权。
    管理员不直接写建议（业务上由专家写）。
    """
    check_expert(current_user)
    work = db.query(FarmWork).filter(FarmWork.id == req.work_id).first()
    if not work:
        raise HTTPException(status_code=404, detail="作业记录不存在")

    # ✅ 权限校验：作业所属农户必须在当前专家的可见范围内
    _assert_can_access_work(work, current_user, db)

    # 仅查询当前专家自己写的建议（避免覆盖别的专家的建议）
    # 一个作业可由多位专家各写一条独立建议
    existing = db.query(ExpertAdvice).filter(
        ExpertAdvice.work_id == req.work_id,
        ExpertAdvice.expert_id == current_user.id,
    ).first()
    if existing:
        existing.content = req.content
    else:
        advice = ExpertAdvice(work_id=req.work_id, expert_id=current_user.id, content=req.content)
        db.add(advice)
    db.commit()
    return {"message": "建议已提交"}


# ========== 专家列表（含好评率） ==========
@router.get("/experts")
def list_experts(db: Session = Depends(get_db)):
    """获取专家列表（含好评率 positive_rate = 4-5星占比%）"""
    experts = db.query(User).filter(User.role == 2, User.status == 1).all()
    result = []
    for e in experts:
        rated = db.query(ExpertQuestion).filter(
            ExpertQuestion.expert_id == e.id,
            ExpertQuestion.status == "已结束",
            ExpertQuestion.rating.isnot(None),
        ).all()
        rating_count = len(rated)
        if rating_count > 0:
            positive = sum(1 for r in rated if r.rating >= 4)
            positive_rate = round(positive * 100 / rating_count, 1)
        else:
            positive_rate = None
        result.append({
            "id": e.id, "name": e.name, "specialty": e.specialty,
            "title": e.title, "bio": e.bio, "avatar": e.avatar,
            "rating_count": rating_count,
            "positive_rate": positive_rate,
        })
    return result


# ========== 专家咨询 IM ==========
@router.post("/questions", response_model=ExpertConsultationResponse)
def create_consultation(req: ExpertConsultationStart, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """农户创建会话并发送首条消息（点击专家进聊天后第一次发送）"""
    expert = db.query(User).filter(User.id == req.expert_id, User.role == 2, User.status == 1).first()
    if not expert:
        raise HTTPException(status_code=404, detail="专家不存在或已下线")
    content = (req.content or "").strip()
    if not content and not req.images:
        raise HTTPException(status_code=400, detail="消息内容不能为空")
    title = content[:30] if content else "图片咨询"
    question = ExpertQuestion(
        user_id=current_user.id, expert_id=req.expert_id,
        title=title, description=content, images=req.images,
        status="进行中",
    )
    db.add(question)
    db.flush()
    db.add(ExpertMessage(
        question_id=question.id, sender_role="farmer", sender_id=current_user.id,
        content=content, images=req.images,
    ))
    db.commit()
    db.refresh(question)
    return _to_consultation(question, current_user.name, db)


@router.post("/questions/{question_id}/messages", response_model=ExpertMessageResponse)
def send_message(question_id: int, req: ExpertMessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """发送消息（农户/专家共用，sender_role 由后端按身份判定）"""
    q = db.query(ExpertQuestion).filter(ExpertQuestion.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="会话不存在")
    is_farmer, is_expert = _is_party(q, current_user)
    if not (is_farmer or is_expert):
        raise HTTPException(status_code=403, detail="无权在此会话发送消息")
    if q.status == "已结束":
        raise HTTPException(status_code=400, detail="会话已结束，无法发送消息")
    content = (req.content or "").strip()
    if not content and not req.images:
        raise HTTPException(status_code=400, detail="消息内容不能为空")
    sender_role = "expert" if is_expert else "farmer"
    msg = ExpertMessage(
        question_id=question_id, sender_role=sender_role, sender_id=current_user.id,
        content=content, images=req.images,
    )
    db.add(msg)
    if sender_role == "expert":
        db.add(Notification(
            user_id=q.user_id,
            question_id=q.id,
            type="consultation",
            title="专家回复了你的咨询",
            content=content[:200] if content else "[图片]",
        ))
    q.description = content[:100] if content else "[图片]"
    q.updated_at = now_china()
    db.commit()
    db.refresh(msg)
    return msg


@router.get("/questions/{question_id}/messages", response_model=list[ExpertMessageResponse])
def list_messages(question_id: int, after_id: int = 0, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """拉取会话消息（轮询增量：after_id 之后的消息）"""
    q = db.query(ExpertQuestion).filter(ExpertQuestion.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="会话不存在")
    is_farmer, is_expert = _is_party(q, current_user)
    if not (is_farmer or is_expert):
        raise HTTPException(status_code=403, detail="无权查看此会话")
    query = db.query(ExpertMessage).filter(ExpertMessage.question_id == question_id)
    if after_id:
        query = query.filter(ExpertMessage.id > after_id)
    return query.order_by(ExpertMessage.id.asc()).all()


@router.post("/questions/{question_id}/end")
def end_consultation(question_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """结束会话（农户或专家均可）。专家结束时自动发送一条预设结束语。

    返回 system_message 字段（仅在专家结束时），方便专家端 push 显示，
    不依赖下一次 list_messages 拉取，避免 race condition 导致看不到结束语。
    """
    q = db.query(ExpertQuestion).filter(ExpertQuestion.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="会话不存在")
    is_farmer, is_expert = _is_party(q, current_user)
    if not (is_farmer or is_expert):
        raise HTTPException(status_code=403, detail="无权结束此会话")
    if q.status == "已结束":
        raise HTTPException(status_code=400, detail="会话已结束")

    # 专家结束时，自动插入一条预设结束语作为消息，并同步未读通知
    closing_msg = None
    if is_expert:
        closing_msg = ExpertMessage(
            question_id=question_id,
            sender_role="expert",
            sender_id=current_user.id,
            content=DEFAULT_EXPERT_CLOSING,
        )
        db.add(closing_msg)
        db.add(Notification(
            user_id=q.user_id,
            question_id=q.id,
            type="consultation",
            title="专家已结束会话",
            content=DEFAULT_EXPERT_CLOSING,
        ))
        q.description = DEFAULT_EXPERT_CLOSING[:100]

    q.status = "已结束"
    q.ended_at = now_china()
    q.ended_by = "expert" if is_expert else "farmer"
    db.commit()
    if closing_msg is not None:
        db.refresh(closing_msg)
    system_message = None
    if closing_msg is not None:
        system_message = {
            "id": closing_msg.id,
            "question_id": question_id,
            "sender_role": "expert",
            "sender_id": current_user.id,
            "content": closing_msg.content,
            "images": None,
            "created_at": closing_msg.created_at.replace(tzinfo=CHINA_TZ).isoformat() if closing_msg.created_at else None,
        }
    return {
        "message": "会话已结束",
        "ended_by": q.ended_by,
        "system_message": system_message,
    }


@router.post("/questions/{question_id}/rate")
def rate_consultation(question_id: int, req: ExpertRateCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """农户评价（仅农户，仅一次，会话结束后可评）"""
    q = db.query(ExpertQuestion).filter(ExpertQuestion.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="会话不存在")
    if q.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="仅农户可评价")
    if q.status != "已结束":
        raise HTTPException(status_code=400, detail="会话未结束，无法评价")
    if q.rating is not None:
        raise HTTPException(status_code=400, detail="已评价，不可重复")
    q.rating = req.rating
    db.commit()
    return {"message": "评价成功", "rating": q.rating}


@router.post("/questions/{question_id}/skip-rating")
def skip_consultation_rating(question_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """农户主动跳过评价（点 × 关闭评价框）。

    跳过后不再显示"待评价"badge，也不再弹出评价框。
    跳过是可逆的：农户再次请求该会话时若想评价，仍可手动调 rate 接口（前端不再展示按钮而已）。
    """
    q = db.query(ExpertQuestion).filter(ExpertQuestion.id == question_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="会话不存在")
    if q.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="仅农户可跳过评价")
    if q.status != "已结束":
        raise HTTPException(status_code=400, detail="会话未结束")
    if q.rating is not None:
        raise HTTPException(status_code=400, detail="已评价")
    if q.rating_skipped_at is not None:
        return {"message": "已跳过", "rating_skipped_at": q.rating_skipped_at}
    q.rating_skipped_at = now_china()
    db.commit()
    db.refresh(q)
    return {"message": "已跳过", "rating_skipped_at": q.rating_skipped_at}


@router.get("/my-consultations", response_model=list[ExpertConsultationResponse])
def my_consultations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """农户：我的会话列表（用于"我的问答"归档）"""
    questions = db.query(ExpertQuestion).filter(
        ExpertQuestion.user_id == current_user.id
    ).order_by(ExpertQuestion.created_at.desc()).all()
    return [_to_consultation(q, current_user.name, db) for q in questions]


@router.get("/my-experts", response_model=list[ExpertConsultationResponse])
def my_experts(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """农户：咨询过的专家列表（按最后咨询时间排序，按 expert_id 去重）

    unread_count 聚合该专家所有会话（含已结束旧会话）的未读通知数，
    避免旧会话的未读通知在归档列表中"消失"但全局未读计数仍为正。
    """
    questions = db.query(ExpertQuestion).filter(
        ExpertQuestion.user_id == current_user.id,
    ).order_by(ExpertQuestion.updated_at.desc()).all()

    seen_experts: set[int] = set()
    result: list[ExpertConsultationResponse] = []
    for q in questions:
        if q.expert_id is None or q.expert_id in seen_experts:
            continue
        seen_experts.add(q.expert_id)
        consultation = _to_consultation(q, current_user.name, db)
        # 聚合该专家所有会话的未读通知数（不只最新一条会话）
        all_qids = [
            qid for (qid,) in db.query(ExpertQuestion.id).filter(
                ExpertQuestion.user_id == current_user.id,
                ExpertQuestion.expert_id == q.expert_id,
            ).all()
        ]
        if all_qids:
            consultation.unread_count = db.query(Notification).filter(
                Notification.user_id == current_user.id,
                Notification.question_id.in_(all_qids),
                Notification.is_read == False,
            ).count()
        result.append(consultation)
    return result


@router.get("/experts/{expert_id}/messages", response_model=list[ExpertMessageResponse])
def list_messages_with_expert(
    expert_id: int,
    after_id: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """农户：与某专家的所有历史消息（跨会话合并，按时间顺序）

    用于"一个专家 = 一个会话栏"的视图：将农户与该专家的所有 ExpertQuestion
    下的 ExpertMessage 合并按 id 升序返回。支持 after_id 增量轮询。
    """
    question_ids = [
        q.id for q in db.query(ExpertQuestion.id).filter(
            ExpertQuestion.user_id == current_user.id,
            ExpertQuestion.expert_id == expert_id,
        ).all()
    ]
    if not question_ids:
        return []
    query = db.query(ExpertMessage).filter(
        ExpertMessage.question_id.in_(question_ids),
    )
    if after_id:
        query = query.filter(ExpertMessage.id > after_id)
    return query.order_by(ExpertMessage.id.asc()).all()


@router.get("/experts/{expert_id}/consultation", response_model=ExpertConsultationResponse)
def get_or_create_consultation(
    expert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """农户：点开专家聊天时调用。

    - 有进行中会话 → 返回该会话（用于续接）
    - 无进行中会话 → 返回一个 id=0 的占位会话（前端发首条消息时调用
      POST /questions 创建真正会话）
    """
    expert = db.query(User).filter(
        User.id == expert_id, User.role == 2, User.status == 1,
    ).first()
    if not expert:
        raise HTTPException(status_code=404, detail="专家不存在或已下线")

    ongoing = db.query(ExpertQuestion).filter(
        ExpertQuestion.user_id == current_user.id,
        ExpertQuestion.expert_id == expert_id,
        ExpertQuestion.status == "进行中",
    ).first()
    if ongoing:
        return _to_consultation(ongoing, current_user.name, db)

    # 返回占位会话：id=0 表示尚未持久化，前端首条消息触发创建
    placeholder = ExpertQuestion(
        id=0, user_id=current_user.id, expert_id=expert_id,
        title="新咨询", description=None, status="待发起",
    )
    return _to_consultation(placeholder, current_user.name, db)


@router.post("/experts/{expert_id}/read-all")
def mark_expert_notifications_read(
    expert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """农户：标记与某专家的所有会话（含已结束旧会话）的未读通知为已读

    解决：旧会话有未读通知但 getOrCreateConsultation 返回占位（id=0）时，
    markConsultationRead(question_id=0) 无法清除旧通知的问题。
    """
    question_ids = [
        qid for (qid,) in db.query(ExpertQuestion.id).filter(
            ExpertQuestion.user_id == current_user.id,
            ExpertQuestion.expert_id == expert_id,
        ).all()
    ]
    if question_ids:
        db.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.question_id.in_(question_ids),
            Notification.is_read == False,
        ).update({"is_read": True})
        db.commit()
    return {"message": "已标记已读"}


@router.post("/upload")
async def upload_image(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    """上传聊天图片，落盘到 uploads/expert/，返回可访问 URL"""
    allowed = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="图片仅支持 jpg/png/webp")
    ext = (file.filename or "x.jpg").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        ext = "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    path = os.path.join("uploads", "expert", filename)
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片不能超过10MB")
    with open(path, "wb") as f:
        f.write(data)
    return {"url": f"/uploads/expert/{filename}"}


# ========== 专家端：会话列表 ==========
@router.get("/questions", response_model=list[ExpertConsultationResponse])
def list_questions(status: str | None = None, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """专家：查看分配给我的会话列表"""
    check_expert(current_user)
    query = db.query(ExpertQuestion).filter(ExpertQuestion.expert_id == current_user.id)
    if status:
        query = query.filter(ExpertQuestion.status == status)
    questions = query.order_by(ExpertQuestion.updated_at.desc()).all()
    result = []
    for q in questions:
        farmer = db.query(User).filter(User.id == q.user_id).first()
        result.append(_to_consultation(q, farmer.name if farmer else "", db))
    return result


@router.get("/notifications/unread-count")
def unread_notification_count(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """农户：未读通知数量（用于导航栏红点）

    只统计咨询类通知（type=consultation），天气推送/节气通知
    由 push/latest + mark-shown 机制单独处理，不混入 QA 红点。
    """
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
        Notification.type == "consultation",
    ).count()
    return {"count": count}


@router.post("/notifications/read-all")
def mark_notifications_read(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """农户：标记所有通知已读"""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"message": "已标记已读"}


@router.post("/notifications/read/{question_id}")
def mark_consultation_read(question_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """农户：标记某个咨询的所有未读通知为已读"""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.question_id == question_id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return {"message": "已标记已读"}
