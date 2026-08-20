"""Pydantic 请求/响应模型"""

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field, field_validator, field_serializer

from app.core.timezone import CHINA_TZ


# ========== Auth ==========
class SendCodeRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$", description="手机号")
    scene: Literal["login", "register", "reset"] = Field(default="login", description="验证码场景")


def _validate_password(value: str) -> str:
    if not 6 <= len(value) <= 20 or not any(char.isalpha() for char in value) or not any(char.isdigit() for char in value):
        raise ValueError("密码需为6-20位，并同时包含字母与数字")
    return value


class RegisterRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    code: str = Field(..., min_length=6, max_length=6)
    password: str = Field(..., min_length=6, max_length=20)
    name: str = Field(..., min_length=1, max_length=50)

    _password_rule = field_validator("password")(_validate_password)


class LoginRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    password: str
    remember: bool = False


class SmsLoginRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    code: str = Field(..., min_length=6, max_length=6)
    remember: bool = False


class ResetPasswordRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    code: str = Field(..., min_length=6, max_length=6)
    password: str = Field(..., min_length=6, max_length=20)

    _password_rule = field_validator("password")(_validate_password)


class TokenResponse(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    must_change_password: bool = False


class ChangeInitialPasswordRequest(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=20)

    _password_rule = field_validator("new_password")(_validate_password)


# ========== User ==========
class UserResponse(BaseModel):
    id: int
    phone: str
    name: str
    role: int
    avatar: str | None = None
    region: str | None = None
    bio: str | None = None
    specialty: str | None = None
    title: str | None = None
    status: int
    adcode: str | None = None
    city: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateRequest(BaseModel):
    name: str | None = None
    avatar: str | None = None
    region: str | None = None
    bio: str | None = None
    specialty: str | None = None
    title: str | None = None


class UserLocationUpdate(BaseModel):
    adcode: str = Field(..., min_length=6, max_length=6)
    city: str = Field(..., min_length=1, max_length=50)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=20)


# ========== Farm Land ==========
class LandCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    region: str = Field(..., min_length=1, max_length=100)
    area: float = Field(..., gt=0)
    soil_type: str | None = None


class LandUpdate(BaseModel):
    name: str | None = None
    region: str | None = None
    area: float | None = None
    soil_type: str | None = None


class LandResponse(BaseModel):
    id: int
    user_id: int
    name: str
    region: str
    area: float
    soil_type: str | None = None
    status: str
    crops: int = 0
    current_crops: list[str] = []
    last_work: str | None = None
    work_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ========== Crop ==========
class CropCreate(BaseModel):
    land_id: int
    name: str = Field(..., min_length=1, max_length=50)
    variety: str | None = None
    plant_date: str


class CropUpdate(BaseModel):
    name: str | None = None
    variety: str | None = None
    plant_date: str | None = None
    stage: str | None = None
    progress: int | None = None
    status: str | None = None


class CropResponse(BaseModel):
    id: int
    user_id: int
    land_id: int
    batch_no: str
    name: str
    variety: str | None = None
    land_name: str = ""
    plant_date: str
    status: str
    harvest_date: str | None = None
    created_at: datetime
    # 列表/首页展示用的聚合字段
    advice_count: int = 0
    work_count: int = 0
    last_work: str | None = None

    model_config = {"from_attributes": True}


# ========== Farm Work ==========
class FarmWorkCreate(BaseModel):
    land_id: int
    batch_id: int
    work_type: str = Field(..., description="整地/播种/施肥/打药/灌溉/采收/其他")
    work_date: str
    description: str = Field(..., min_length=1)
    photos: str | None = None


class FarmWorkUpdate(BaseModel):
    work_type: str | None = None
    work_date: str | None = None
    description: str | None = None
    photos: str | None = None


class FarmWorkAdviceItem(BaseModel):
    """农户作业记录下的单条专家建议（用于农户端展示是哪个专家写的）"""
    expert_id: int
    expert_name: str | None = None
    content: str
    is_read: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class FarmWorkResponse(BaseModel):
    id: int
    user_id: int
    land_id: int
    batch_id: int
    work_type: str
    work_date: str
    land_name: str = ""
    batch_no: str = ""
    description: str
    photos: str | None = None
    has_photo: bool = False
    advice: str | None = None
    # 农户端可见：该作业所有专家写的建议（含 expert_name，让农户知道是哪个专家写的）
    # 专家端 list_all_works 不填该字段（默认空），专家只通过 advice 字段看自己写的那条
    advices: list[FarmWorkAdviceItem] = []
    farmer_name: str | None = None
    farmer_phone: str | None = None
    # 批次详情（用于专家端按批次分组展示）
    crop_name: str = ""
    crop_variety: str | None = None
    crop_status: str = ""
    plant_date: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ========== FarmPlan（农事计划） ==========
class FarmPlanCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=200, description="计划内容")
    plan_date: str | None = Field(None, description="计划日期 YYYY-MM-DD，默认今天")


class FarmPlanUpdate(BaseModel):
    is_done: bool


class FarmPlanResponse(BaseModel):
    id: int
    content: str
    plan_date: str
    is_done: bool
    done_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ========== Article ==========
class ArticleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    category: str
    content: str
    summary: str | None = None
    cover: str | None = None
    source: str | None = None
    original_author: str | None = None


class ArticleUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    content: str | None = None
    summary: str | None = None
    cover: str | None = None
    source: str | None = None
    original_author: str | None = None


class ArticleResponse(BaseModel):
    id: int
    author_id: int
    author_name: str = ""
    author_role: int | None = None
    title: str
    category: str
    content: str = ""
    summary: str | None = None
    cover: str | None = None
    source: str | None = None
    original_author: str | None = None
    review_status: str = "published"
    review_reason: str | None = None
    date: str = ""
    created_at: datetime
    published_at: datetime | None = None

    model_config = {"from_attributes": True}


class ArticleReviewRequest(BaseModel):
    action: str = Field(..., pattern=r"^(approve|reject)$")
    reason: str | None = None


# ========== Expert ==========
class ExpertAdviceCreate(BaseModel):
    work_id: int
    content: str


class ExpertQuestionCreate(BaseModel):
    title: str
    crop: str | None = None
    description: str | None = None
    images: str | None = None
    expert_id: int | None = None


class ExpertAnswerCreate(BaseModel):
    content: str


class ExpertQuestionResponse(BaseModel):
    id: int
    user_id: int
    expert_id: int | None = None
    expert_name: str | None = None
    farmer_name: str = ""
    title: str
    crop: str | None = None
    description: str | None = None
    images: str | None = None
    has_image: bool = False
    answer: str | None = None
    status: str
    date: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}


# ========== 专家咨询 IM ==========
class ExpertConsultationStart(BaseModel):
    expert_id: int
    content: str
    images: str | None = None


class ExpertMessageCreate(BaseModel):
    content: str
    images: str | None = None


class ExpertMessageResponse(BaseModel):
    id: int
    question_id: int
    sender_role: str
    sender_id: int
    content: str
    images: str | None = None
    created_at: datetime

    @field_serializer('created_at')
    def serialize_created_at(self, value: datetime) -> str:
        return value.replace(tzinfo=CHINA_TZ).isoformat()

    model_config = {"from_attributes": True}


class ExpertConsultationResponse(BaseModel):
    id: int
    expert_id: int | None = None
    expert_name: str | None = None
    expert_avatar: str | None = None
    expert_title: str | None = None
    expert_specialty: str | None = None
    farmer_id: int | None = None
    farmer_name: str = ""
    farmer_avatar: str | None = None
    title: str
    last_preview: str | None = None
    status: str
    rating: int | None = None
    rating_skipped_at: datetime | None = None
    unread_count: int = 0
    ended_at: datetime | None = None
    ended_by: str | None = None
    # 专家端软提示：农户空闲了多少分钟（仅当会话进行中且最后一条消息是专家发的且 >= 15 分钟时填）
    farmer_idle_minutes: int | None = None
    created_at: datetime
    updated_at: datetime | None = None

    @field_serializer('created_at', 'updated_at', 'ended_at', 'rating_skipped_at')
    def serialize_consultation_datetimes(self, value: datetime | None) -> str | None:
        if value is None:
            return None
        return value.replace(tzinfo=CHINA_TZ).isoformat()

    model_config = {"from_attributes": True}


class ExpertRateCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5)


# ========== AI Knowledge Q&A ==========
class AIConversationResponse(BaseModel):
    id: int
    title: str
    agent_type: str = "knowledge"
    created_at: datetime
    updated_at: datetime

    @field_serializer('created_at', 'updated_at')
    def serialize_ai_conversation_datetimes(self, value: datetime) -> str:
        return value.replace(tzinfo=CHINA_TZ).isoformat()

    model_config = {"from_attributes": True}


class AIMessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    image_name: str | None = None
    image_urls: str | None = None
    image_analysis: str | None = None
    sources: str | None = None
    created_at: datetime

    @field_serializer('created_at')
    def serialize_ai_message_created_at(self, value: datetime) -> str:
        return value.replace(tzinfo=CHINA_TZ).isoformat()

    model_config = {"from_attributes": True}


# ========== Admin ==========
class AdminUserUpdate(BaseModel):
    status: int | None = None
    name: str | None = None


class AdminExpertUpdate(BaseModel):
    name: str | None = None
    specialty: str | None = None
    title: str | None = None
    bio: str | None = None
    status: int | None = None


class AdminExpertCreate(BaseModel):
    phone: str = Field(..., pattern=r"^1[3-9]\d{9}$")
    name: str
    password: str = Field(..., min_length=6, max_length=20)
    specialty: str | None = None
    title: str | None = None
    bio: str | None = None


class AdminStatsResponse(BaseModel):
    users: int
    experts: int
    articles: int
    pending_articles: int = 0
    questions: int
    active_today: int
    land_plots: int
