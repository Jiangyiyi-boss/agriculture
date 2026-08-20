"""SQLAlchemy 数据库模型"""

from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean, Enum as SAEnum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.timezone import now_china


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    phone = Column(String(11), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    name = Column(String(50), nullable=False)
    role = Column(Integer, nullable=False, default=1, comment="1=农户 2=专家 3=管理员")
    avatar = Column(String(255), nullable=True)
    region = Column(String(100), nullable=True, comment="所在地区")
    adcode = Column(String(6), nullable=True, comment="高德行政区划代码(用于天气推送)")
    city = Column(String(50), nullable=True, comment="城市名(用于展示)")
    adcode_updated_at = Column(DateTime, nullable=True, comment="位置更新时间")
    bio = Column(String(500), nullable=True, comment="个人简介")
    specialty = Column(String(200), nullable=True, comment="专家专业领域")
    title = Column(String(50), nullable=True, comment="专家职称")
    status = Column(Integer, nullable=False, default=1, comment="0=禁用 1=正常")
    must_change_password = Column(Boolean, default=False, comment="是否需要强制修改密码（管理员创建专家时为 True）")
    created_at = Column(DateTime, default=now_china)
    updated_at = Column(DateTime, default=now_china, onupdate=now_china)

    # 关系
    lands = relationship("FarmLand", back_populates="owner")
    crops = relationship("CropManagement", back_populates="owner")
    farm_works = relationship("FarmWork", back_populates="owner")
    articles = relationship("Article", back_populates="author", foreign_keys="Article.author_id")
    expert_advice = relationship("ExpertAdvice", back_populates="expert")
    questions = relationship("ExpertQuestion", back_populates="farmer", foreign_keys="ExpertQuestion.user_id")
    answers = relationship("ExpertAnswer", back_populates="expert")
    ai_conversations = relationship("AIConversation", back_populates="user")


class FarmLand(Base):
    __tablename__ = "farm_lands"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False, comment="地块名称")
    region = Column(String(100), nullable=False, comment="所在地")
    area = Column(Float, nullable=False, comment="面积(亩)")
    soil_type = Column(String(20), nullable=True, comment="土壤类型")
    status = Column(String(10), nullable=False, default="空闲", comment="种植中/空闲")
    created_at = Column(DateTime, default=now_china)
    updated_at = Column(DateTime, default=now_china, onupdate=now_china)

    owner = relationship("User", back_populates="lands")
    crops = relationship("CropManagement", back_populates="land")


class CropManagement(Base):
    __tablename__ = "crop_management"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    land_id = Column(Integer, ForeignKey("farm_lands.id"), nullable=False)
    batch_no = Column(String(20), unique=True, nullable=False, comment="生产批次号")
    name = Column(String(50), nullable=False, comment="作物名称")
    variety = Column(String(50), nullable=True, comment="品种")
    plant_date = Column(DateTime, nullable=False, comment="种植时间")
    harvest_date = Column(DateTime, nullable=True, comment="预计采收时间")
    stage = Column(String(20), nullable=True, default="苗期", comment="当前生长阶段")
    progress = Column(Integer, nullable=True, default=0, comment="生长进度百分比")
    status = Column(String(10), nullable=False, default="种植中", comment="种植中/已采收")
    created_at = Column(DateTime, default=now_china)
    updated_at = Column(DateTime, default=now_china, onupdate=now_china)

    owner = relationship("User", back_populates="crops")
    land = relationship("FarmLand", back_populates="crops")
    farm_works = relationship("FarmWork", back_populates="batch")


class FarmWork(Base):
    __tablename__ = "farm_works"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    land_id = Column(Integer, ForeignKey("farm_lands.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("crop_management.id"), nullable=False)
    work_type = Column(String(10), nullable=False, comment="整地/播种/施肥/打药/灌溉/采收/其他")
    work_date = Column(DateTime, nullable=False, comment="作业日期")
    description = Column(Text, nullable=False, comment="作业描述")
    photos = Column(Text, nullable=True, comment="照片URL(逗号分隔)")
    created_at = Column(DateTime, default=now_china)
    updated_at = Column(DateTime, default=now_china, onupdate=now_china)

    owner = relationship("User", back_populates="farm_works")
    batch = relationship("CropManagement", back_populates="farm_works")
    expert_advice = relationship("ExpertAdvice", back_populates="farm_work")


class FarmPlan(Base):
    """农户农事计划（首页"今日农事"卡片）"""

    __tablename__ = "farm_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(String(200), nullable=False, comment="计划内容")
    plan_date = Column(DateTime, nullable=False, comment="计划日期(当天0点)")
    is_done = Column(Boolean, default=False, comment="是否完成")
    done_at = Column(DateTime, nullable=True, comment="完成时间")
    created_at = Column(DateTime, default=now_china)


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    category = Column(String(20), nullable=False, comment="政策解读/种植技术/病虫害防治/市场行情/平台公告")
    content = Column(Text, nullable=False, comment="文章内容")
    summary = Column(String(500), nullable=True, comment="摘要")
    cover = Column(String(255), nullable=True, comment="封面图")
    source = Column(String(100), nullable=True, comment="文章来源，如'农业农村部信息中心'")
    original_author = Column(String(50), nullable=True, comment="原文作者（转载时填写）")
    review_status = Column(String(20), nullable=False, default="published", comment="pending/published/rejected")
    review_reason = Column(Text, nullable=True, comment="审核意见")
    reviewed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=now_china)
    updated_at = Column(DateTime, default=now_china, onupdate=now_china)

    author = relationship("User", back_populates="articles", foreign_keys=[author_id])


class ExpertAdvice(Base):
    __tablename__ = "expert_advice"

    id = Column(Integer, primary_key=True, autoincrement=True)
    work_id = Column(Integer, ForeignKey("farm_works.id"), nullable=False)
    expert_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, comment="农户是否已查看该建议")
    created_at = Column(DateTime, default=now_china)

    farm_work = relationship("FarmWork", back_populates="expert_advice")
    expert = relationship("User", back_populates="expert_advice")


class ArticleView(Base):
    __tablename__ = "article_views"
    __table_args__ = (UniqueConstraint("user_id", "article_id", name="uq_user_article"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False, index=True)
    viewed_at = Column(DateTime, default=now_china, onupdate=now_china, comment="最近浏览时间")


class ExpertQuestion(Base):
    __tablename__ = "expert_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    expert_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String(200), nullable=False)
    crop = Column(String(50), nullable=True, comment="相关作物")
    description = Column(Text, nullable=True, comment="问题描述")
    images = Column(Text, nullable=True, comment="图片URL(逗号分隔)")
    status = Column(String(10), nullable=False, default="进行中", comment="进行中/已结束")
    rating = Column(Integer, nullable=True, comment="农户评分1-5")
    rating_skipped_at = Column(DateTime, nullable=True, comment="农户主动跳过评价时间")
    ended_at = Column(DateTime, nullable=True, comment="会话结束时间")
    ended_by = Column(String(10), nullable=True, comment="结束方: farmer/expert")
    created_at = Column(DateTime, default=now_china)
    updated_at = Column(DateTime, default=now_china, onupdate=now_china)

    farmer = relationship("User", back_populates="questions", foreign_keys=[user_id])
    answers = relationship("ExpertAnswer", back_populates="question")
    messages = relationship("ExpertMessage", back_populates="question", order_by="ExpertMessage.id", cascade="all, delete-orphan")


class ExpertAnswer(Base):
    __tablename__ = "expert_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("expert_questions.id"), nullable=False)
    expert_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=now_china)

    question = relationship("ExpertQuestion", back_populates="answers")
    expert = relationship("User", back_populates="answers")


class ExpertMessage(Base):
    """专家咨询聊天消息（IM 即时通讯）"""
    __tablename__ = "expert_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("expert_questions.id"), nullable=False, index=True)
    sender_role = Column(String(10), nullable=False, comment="farmer/expert")
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    images = Column(Text, nullable=True, comment="图片URL(逗号分隔)")
    created_at = Column(DateTime, default=now_china, index=True)

    question = relationship("ExpertQuestion", back_populates="messages")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("expert_questions.id"), nullable=True, comment="关联的咨询ID")
    type = Column(String(20), nullable=False, comment="通知类型")
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now_china)
    rule_code = Column(String(50), nullable=True, index=True,
                       comment="天气规则代码，如 high_temp/frost/rain_heavy/wind，用于去重")


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(100), nullable=False, default="新的农业问题")
    agent_type = Column(String(30), nullable=False, default="knowledge", comment="knowledge/planting/pest")
    created_at = Column(DateTime, default=now_china)
    updated_at = Column(DateTime, default=now_china, onupdate=now_china)

    user = relationship("User", back_populates="ai_conversations")
    messages = relationship("AIMessage", back_populates="conversation", cascade="all, delete-orphan")


class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey("ai_conversations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String(20), nullable=False, comment="user/assistant/system")
    content = Column(Text, nullable=False)
    image_name = Column(String(255), nullable=True)
    image_mime = Column(String(80), nullable=True)
    image_size = Column(Integer, nullable=True)
    image_urls = Column(String(500), nullable=True, comment="逗号分隔的图片访问URL，持久化保存")
    image_analysis = Column(Text, nullable=True)
    sources = Column(Text, nullable=True, comment="JSON encoded search sources")
    created_at = Column(DateTime, default=now_china)

    conversation = relationship("AIConversation", back_populates="messages")


class AiMemory(Base):
    """AI 长期记忆：一条条独立事实条目，支持溯源与单条管理"""

    __tablename__ = "ai_memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(String(500), nullable=False, comment="单条记忆事实")
    conversation_id = Column(Integer, ForeignKey("ai_conversations.id"), nullable=True, comment="来源会话（溯源）")
    created_at = Column(DateTime, default=now_china)
    updated_at = Column(DateTime, default=now_china, onupdate=now_china)


class PestKnowledge(Base):
    __tablename__ = "pest_knowledge"

    id = Column(Integer, primary_key=True, autoincrement=True)
    crop_name = Column(String(80), nullable=False, index=True, comment="作物名称")
    pest_name = Column(String(120), nullable=False, index=True, comment="病虫害名称")
    category = Column(String(20), nullable=False, default="虫害", comment="虫害/病害")
    intro = Column(Text, nullable=True, comment="简介")
    symptoms = Column(Text, nullable=True, comment="危害症状")
    cause = Column(Text, nullable=True, comment="发生因素")
    habit = Column(Text, nullable=True, comment="生活习性")
    morphology = Column(Text, nullable=True, comment="形态特征")
    control_method = Column(Text, nullable=True, comment="防治方法")
    source_file = Column(String(255), nullable=True, comment="来源文件")
    vector_text = Column(Text, nullable=False, comment="用于向量化的知识文本")
    created_at = Column(DateTime, default=now_china)
    updated_at = Column(DateTime, default=now_china, onupdate=now_china)


class CropSuitability(Base):
    """作物适宜性数据（来源：作物适宜性数据.csv）"""

    __tablename__ = "crop_suitability"

    id = Column(Integer, primary_key=True, autoincrement=True)
    crop_name = Column(String(50), nullable=False, index=True, comment="作物名称")
    category = Column(String(20), nullable=False, comment="粮食作物/蔬菜/水果/经济作物")
    varieties = Column(String(200), nullable=True, comment="代表品种")
    temp_range = Column(String(50), nullable=True, comment="适宜温度范围原文")
    temp_min = Column(Float, nullable=True, comment="温度下限(℃)")
    temp_max = Column(Float, nullable=True, comment="温度上限(℃)")
    soil_types = Column(String(100), nullable=True, comment="适宜土壤类型")
    ph_range = Column(String(20), nullable=True, comment="适宜pH范围原文")
    ph_min = Column(Float, nullable=True, comment="pH下限")
    ph_max = Column(Float, nullable=True, comment="pH上限")
    growth_cycle = Column(String(50), nullable=True, comment="生长周期原文")
    cycle_min = Column(Integer, nullable=True, comment="周期下限(天)")
    cycle_max = Column(Integer, nullable=True, comment="周期上限(天)")
    is_perennial = Column(Boolean, default=False, comment="是否多年生")
    water_demand = Column(String(10), nullable=True, comment="需水量: 高/中/低")
    light_requirement = Column(String(20), nullable=True, comment="光照要求")
    main_diseases = Column(String(200), nullable=True, comment="主要病害")
    sow_seasons = Column(String(100), nullable=True, comment="适宜播种季节")
    cold_resistance = Column(String(10), nullable=True, comment="耐寒性: 高/中/低")
    drought_resistance = Column(String(10), nullable=True, comment="耐旱性: 高/中/低")
    region_fit = Column(String(20), nullable=True, index=True, comment="地域适配: 南方为主/北方为主/全国通用")
    yield_ref = Column(String(100), nullable=True, comment="亩产参考原文")
    yield_min = Column(Float, nullable=True, comment="亩产下限(kg)")
    yield_max = Column(Float, nullable=True, comment="亩产上限(kg)")
    created_at = Column(DateTime, default=now_china)


class SoilData(Base):
    """土壤数据（来源：土壤数据汇总表.xlsx）"""

    __tablename__ = "soil_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    province = Column(String(20), nullable=False, index=True, comment="省名")
    city = Column(String(50), nullable=True, index=True, comment="地级市名")
    county = Column(String(50), nullable=True, index=True, comment="县市名")
    soil_group = Column(String(50), nullable=True, comment="土纲名")
    subgroup = Column(String(50), nullable=True, comment="亚类名")
    soil_species = Column(String(50), nullable=True, comment="土种名")
    texture = Column(String(20), nullable=True, comment="质地")
    organic_matter = Column(Float, nullable=True, comment="有机质(g/kg)")
    ph_value = Column(String(20), nullable=True, comment="pH值原文")
    ph_min = Column(Float, nullable=True, comment="pH下限")
    ph_max = Column(Float, nullable=True, comment="pH上限")
    created_at = Column(DateTime, default=now_china)


class AdminDistrict(Base):
    """行政区划映射（来源：行政区划映射表.xlsx）"""

    __tablename__ = "admin_district"

    id = Column(Integer, primary_key=True, autoincrement=True)
    province = Column(String(20), nullable=False, index=True, comment="省份")
    city = Column(String(50), nullable=True, index=True, comment="地级市")
    county = Column(String(50), nullable=True, index=True, comment="区县")
    level = Column(String(10), nullable=True, comment="级别: 区/县/市")
    aliases = Column(String(500), nullable=True, comment="别名(竖线分隔)")
    created_at = Column(DateTime, default=now_china)
