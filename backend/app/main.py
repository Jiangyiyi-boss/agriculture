"""慧农宝 - FastAPI 主入口"""

import asyncio
import logging
import os
import sys
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta

# Windows 下 psycopg 异步需要 SelectorEventLoop，必须在任何 async 代码前设置
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text

from app.core.config import settings
from app.core.database import engine, Base, SessionLocal

# 配置日志：病虫害 RAG 调试日志同时输出到控制台和文件
# 兼容 Docker（/app/）和本地（当前目录）两种环境
_log_path = "/app/pest_debug.log" if os.path.isdir("/app") else "pest_debug.log"
_file_handler = logging.FileHandler(_log_path, encoding="utf-8")
_file_handler.setLevel(logging.INFO)
_stream_handler = logging.StreamHandler()
_stream_handler.setLevel(logging.INFO)
_formatter = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S")
_file_handler.setFormatter(_formatter)
_stream_handler.setFormatter(_formatter)
logging.basicConfig(level=logging.INFO, handlers=[_file_handler, _stream_handler])


def ensure_article_review_columns():
    """补齐旧数据库的文章审核字段，避免开发库需要手动重建表。"""
    inspector = inspect(engine)
    if not inspector.has_table("articles"):
        return

    existing = {column["name"] for column in inspector.get_columns("articles")}
    columns = {
        "review_status": "VARCHAR(20) NOT NULL DEFAULT 'published'",
        "review_reason": "TEXT NULL",
        "reviewed_by": "INT NULL",
        "reviewed_at": "DATETIME NULL",
        "published_at": "DATETIME NULL",
    }

    with engine.begin() as conn:
        dialect = engine.dialect.name
        for name, definition in columns.items():
            if name in existing:
                continue
            if dialect == "sqlite":
                sqlite_definition = definition.replace("INT", "INTEGER").replace("DATETIME", "DATETIME")
                conn.execute(text(f"ALTER TABLE articles ADD COLUMN {name} {sqlite_definition}"))
            else:
                conn.execute(text(f"ALTER TABLE articles ADD COLUMN {name} {definition}"))
        conn.execute(text("UPDATE articles SET review_status = 'published' WHERE review_status IS NULL"))
        conn.execute(text("UPDATE articles SET published_at = created_at WHERE published_at IS NULL AND review_status = 'published'"))


def ensure_expert_question_columns():
    """补齐旧数据库的专家咨询字段（expert_id/rating/ended_at/ended_by）。"""
    inspector = inspect(engine)
    if not inspector.has_table("expert_questions"):
        return

    existing = {column["name"] for column in inspector.get_columns("expert_questions")}
    needed = {
        "expert_id": "INTEGER NULL",
        "rating": "INTEGER NULL",
        "rating_skipped_at": "DATETIME NULL",
        "ended_at": "DATETIME NULL",
        "ended_by": "VARCHAR(10) NULL",
    }
    with engine.begin() as conn:
        for name, definition in needed.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE expert_questions ADD COLUMN {name} {definition}"))


def ensure_notification_question_id_column():
    """补齐旧通知表的 question_id 字段。"""
    inspector = inspect(engine)
    if not inspector.has_table("notifications"):
        return
    existing = {column["name"] for column in inspector.get_columns("notifications")}
    if "question_id" not in existing:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE notifications ADD COLUMN question_id INTEGER NULL"))


def ensure_notification_rule_code_column():
    """补齐旧通知表的 rule_code 字段（用于天气推送去重）。"""
    inspector = inspect(engine)
    if not inspector.has_table("notifications"):
        return
    existing = {column["name"] for column in inspector.get_columns("notifications")}
    if "rule_code" not in existing:
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE notifications ADD COLUMN rule_code VARCHAR(50) NULL "
                "COMMENT '天气规则代码，用于去重'"
            ))
            try:
                conn.execute(text(
                    "CREATE INDEX idx_notifications_rule_code ON notifications(rule_code)"
                ))
            except Exception:
                pass  # 索引可能已存在


def ensure_user_adcode_columns():
    """补齐旧用户表的 adcode/city 字段（用于天气推送地域分组）。"""
    inspector = inspect(engine)
    if not inspector.has_table("users"):
        return
    existing = {column["name"] for column in inspector.get_columns("users")}
    needed = {
        "adcode": "VARCHAR(6) NULL",
        "city": "VARCHAR(50) NULL",
        "adcode_updated_at": "DATETIME NULL",
    }
    with engine.begin() as conn:
        for name, definition in needed.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {name} {definition}"))


def ensure_expert_advice_is_read_column():
    """补齐 expert_advice 表的 is_read 字段（用于农户查看建议后标记已读）。"""
    inspector = inspect(engine)
    if not inspector.has_table("expert_advice"):
        return
    existing = {column["name"] for column in inspector.get_columns("expert_advice")}
    if "is_read" not in existing:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE expert_advice ADD COLUMN is_read TINYINT(1) DEFAULT 0"))


def ensure_user_must_change_password_column():
    """补齐 users 表的 must_change_password 字段（专家首次登录强制改密码）。"""
    inspector = inspect(engine)
    if not inspector.has_table("users"):
        return
    existing = {column["name"] for column in inspector.get_columns("users")}
    if "must_change_password" not in existing:
        with engine.begin() as conn:
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN must_change_password TINYINT(1) DEFAULT 0 "
                "COMMENT '是否需要强制修改密码'"
            ))


def ensure_article_source_column():
    """补齐 articles 表的 source/original_author 字段（文章来源与原文作者）。"""
    inspector = inspect(engine)
    if not inspector.has_table("articles"):
        return
    existing = {column["name"] for column in inspector.get_columns("articles")}
    with engine.begin() as conn:
        if "source" not in existing:
            conn.execute(text(
                "ALTER TABLE articles ADD COLUMN source VARCHAR(100) NULL "
                "COMMENT '文章来源'"
            ))
        if "original_author" not in existing:
            conn.execute(text(
                "ALTER TABLE articles ADD COLUMN original_author VARCHAR(50) NULL "
                "COMMENT '原文作者（转载时填写）'"
            ))


_logger = logging.getLogger("main")
_scheduler_stop = threading.Event()


def _has_solar_term_pushed_today() -> bool:
    """检查今天是否已推过节气（用于重启后跳过节气补跑）。

    节气当日去重：每个节气每年对每个农户只推 1 次，重启不重复推。
    """
    from app.models import Notification
    from app.core.timezone import now_china

    db = SessionLocal()
    try:
        start = now_china().replace(hour=0, minute=0, second=0, microsecond=0)
        return db.query(Notification).filter(
            Notification.type == "solar_term",
            Notification.created_at >= start,
        ).count() > 0
    finally:
        db.close()


def _scheduler_loop():
    """后台线程：6:00 定时推节气 + 每 30 分钟轮询气象预警。

    调度策略（2026-08 重构）：
    - 6:00 定时任务：只推节气（lunar_python 天文算法匹配当日，当年去重）
    - 30 分钟轮询（6:00-23:00）：查和风气象预警（暴雨/高温/大风/寒潮等）
    - 23:00-6:00 不轮询（农户睡觉，预警由下一次轮询补推）

    补跑逻辑：
    - 启动时若 6:00 已过且当天未推节气 → 立即补推节气
    - 轮询任务无需补跑（下次 30 分钟就到）
    """
    _logger.info("[推送调度] 后台线程已启动（6:00 节气 + 30 分钟预警轮询）")

    from app.core.timezone import now_china

    # 启动补跑：若 6:00 已过且今天没推过节气 → 立即补推
    try:
        now = now_china()
        if now.hour >= 6 and not _has_solar_term_pushed_today():
            _logger.info("[推送调度] 启动补跑：今天尚未推节气，立即执行")
            from app.services.push_agent import run_solar_term_push
            count = run_solar_term_push(logger=_logger)
            _logger.info(f"[推送调度] 节气补跑完成: {count} 条")
        else:
            _logger.info("[推送调度] 节气今日已推或未到时间，跳过补跑")
    except Exception as e:
        _logger.error(f"[推送调度] 节气补跑异常: {e}", exc_info=True)

    # 上次执行节气/轮询的日期+小时标记，避免同一时间段重复执行
    # 注意：last_solar_date 初始化为 None，不能预设为今天，否则 6:00 主循环会
    # 因 last_solar_date == today_str 误判"今天已推过"而跳过（即便实际没推过）。
    # 当年去重由 create_solar_term_notifications 通过 MySQL rule_code 兜底。
    last_solar_date = None
    last_poll_slot = None  # "YYYY-MM-DD HH:MM" 格式（按 30 分钟取整）

    while not _scheduler_stop.is_set():
        now = now_china()
        today_str = now.strftime("%Y-%m-%d")
        # 当前 30 分钟时间段标记（如 "2026-08-19 14:30"）
        slot_minute = 0 if now.minute < 30 else 30
        current_slot = now.strftime("%Y-%m-%d %H:") + f"{slot_minute:02d}"

        # ===== 6:00 定时任务：推节气 =====
        if now.hour == 6 and 0 <= now.minute < 30 and last_solar_date != today_str:
            last_solar_date = today_str
            _logger.info("[推送调度] 6:00 定时任务：执行节气推送")
            try:
                from app.services.push_agent import run_solar_term_push
                count = run_solar_term_push(logger=_logger)
                _logger.info(f"[推送调度] 节气推送完成: {count} 条")
            except Exception as e:
                _logger.error(f"[推送调度] 节气推送异常: {e}", exc_info=True)

        # ===== 30 分钟轮询：6:00-23:00 查气象预警 =====
        if 6 <= now.hour <= 23 and current_slot != last_poll_slot:
            last_poll_slot = current_slot
            _logger.info(f"[推送调度] {current_slot} 轮询任务：查气象预警")
            try:
                from app.services.push_agent import run_weather_poll_push
                count = run_weather_poll_push(logger=_logger)
                _logger.info(f"[推送调度] 轮询完成: {count} 条预警")
            except Exception as e:
                _logger.error(f"[推送调度] 轮询异常: {e}", exc_info=True)

        # 每 60 秒检查一次
        time.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时创建数据库表，启动推送定时器"""
    Base.metadata.create_all(bind=engine)
    ensure_article_review_columns()
    ensure_expert_question_columns()
    ensure_notification_question_id_column()
    ensure_notification_rule_code_column()
    ensure_user_adcode_columns()
    ensure_expert_advice_is_read_column()
    ensure_user_must_change_password_column()
    ensure_article_source_column()

    # 启动推送定时调度
    _scheduler_stop.clear()
    scheduler_thread = threading.Thread(target=_scheduler_loop, daemon=True, name="push-scheduler")
    scheduler_thread.start()

    yield

    # 关闭时停止调度
    _scheduler_stop.set()


app = FastAPI(
    title="慧农宝 API",
    description="慧农宝 - 智能农业管理平台后端服务",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads/articles", exist_ok=True)
os.makedirs("uploads/expert", exist_ok=True)
os.makedirs("uploads/farmwork", exist_ok=True)
os.makedirs("uploads/avatar", exist_ok=True)
os.makedirs("uploads/ai_chat", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 注册路由
from app.api.auth import router as auth_router
from app.api.user import router as user_router
from app.api.land import router as land_router
from app.api.crop import router as crop_router
from app.api.farm_work import router as farm_work_router
from app.api.article import router as article_router
from app.api.expert import router as expert_router
from app.api.admin import router as admin_router
from app.api.location import router as location_router
from app.api.ai import router as ai_router
from app.api.push import router as push_router
from app.api.plan import router as plan_router

app.include_router(auth_router)
app.include_router(user_router)
app.include_router(land_router)
app.include_router(crop_router)
app.include_router(farm_work_router)
app.include_router(article_router)
app.include_router(expert_router)
app.include_router(admin_router)
app.include_router(location_router)
app.include_router(ai_router)
app.include_router(push_router)
app.include_router(plan_router)


@app.get("/")
def root():
    return {"name": "慧农宝 API", "version": "0.1.0", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}
