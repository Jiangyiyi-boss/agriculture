"""推送 Agent — 节气提醒 + 天气预警

架构（2026-08）：
- 6:00 定时：只推节气（lunar_python 天文算法精确匹配当日，当年去重）
- 30 分钟轮询（6:00-23:00）：
    - 查和风气象预警 /weatheralert/v1/current → 暴雨/高温/大风/寒潮等（按预警 ID 去重）

数据源：高德（地理编码/前端定位）+ 和风（天气数据）
高德的天气调用已废弃，保留 geocode/regeo 用于地名↔坐标互转。

注：降雨提醒已移除（分钟级降水 API 对微量降水过于敏感，容易误报）。
"""

from datetime import date, datetime, timedelta
from typing import Any

# ============================================================
# 24 节气文案配置（仅文案，日期由 lunar_python 天文算法精确计算）
# ============================================================

SOLAR_TERMS: dict[str, dict[str, str]] = {
    "立春": {"title": "🌱 立春到，春意萌动", "content": "立春到，春意萌动。早稻产区开始备种，冬小麦即将返青。农闲即将结束，您准备好春耕了吗？"},
    "雨水": {"title": "💧 雨水至，及时防渍", "content": "雨水至，降雨增多。油菜进入花期，注意清沟排水防渍。湿度大时易发病，建议提前预防。"},
    "惊蛰": {"title": "⚡ 惊蛰到，春雷响", "content": "惊蛰到，春雷响，万物长。建议您开始春耕备种，翻地施肥，为春播做准备。"},
    "春分": {"title": "🌸 春分，昼夜平分", "content": "春分时节，昼夜平分。早稻播种正当时，蔬菜可以大面积定植了。平衡施肥，促进作物生长。"},
    "清明": {"title": "🌿 清明前后，种瓜点豆", "content": "清明前后，种瓜点豆。适合播种瓜类、豆类作物，您计划好种什么了吗？"},
    "谷雨": {"title": "🌾 谷雨，早稻移栽", "content": "谷雨时节，雨量增多。早稻可以开始移栽了，注意保持田间水位，适时追施返青肥。"},
    "立夏": {"title": "☀️ 立夏，夏收准备", "content": "立夏到，夏收作物进入灌浆期。小麦、油菜即将成熟，提前准备收割工具和晾晒场地。"},
    "小满": {"title": "🌾 小满，麦粒渐满", "content": "小满小满，麦粒渐满。冬小麦进入灌浆关键期，注意防治病虫害，确保丰收。"},
    "芒种": {"title": "🏃 芒种忙，晚稻播种", "content": "芒种忙，忙着种。晚稻播种正当时，不要错过农时。同时注意夏收作物及时晾晒入库。"},
    "夏至": {"title": "☀️ 夏至，防暑降温", "content": "夏至到，高温来临。提醒您避开中午下地，注意防暑防晒。水稻注意深水灌溉降温。"},
    "小暑": {"title": "🔥 小暑，防旱防虫", "content": "小暑大暑，上蒸下煮。注意田间灌溉防旱，同时也是病虫害高发期，定期检查防治。"},
    "大暑": {"title": "🔥 大暑，防高温热害", "content": "大暑到，高温热害风险高。水稻注意深水灌溉，果树注意防晒，蔬菜可加盖遮阳网。"},
    "立秋": {"title": "🍂 立秋，秋收准备", "content": "立秋到，秋作物陆续进入成熟期。开始准备秋收工具和晾晒场地，农忙即将开始。"},
    "处暑": {"title": "🌾 处暑，秋收开始", "content": "处暑到，秋收正式开始。中稻、玉米陆续成熟，及时收割晾晒，注意天气变化抢收。"},
    "白露": {"title": "🍂 白露，天气转凉", "content": "白露到，天气转凉。秋作物进入成熟期，随时关注及时收获。早晚温差大，注意防寒。"},
    "秋分": {"title": "🌾 秋分，丰收忙", "content": "秋分时节，丰收忙。晚稻开始收割，抓紧好天气晾晒入库。秋播作物可以开始播种了。"},
    "寒露": {"title": "🧥 寒露，防寒保暖", "content": "寒露到，气温下降。注意防霜冻，抓紧完成秋收。冬小麦开始播种。"},
    "霜降": {"title": "❄️ 霜降，防霜冻", "content": "霜降杀百草，露水变霜。注意防霜冻，及时收获冬储蔬菜，防止冻害。"},
    "立冬": {"title": "🌨️ 立冬，冬小麦播种", "content": "立冬到，冬小麦播种扫尾。注意防冻保苗，晚稻产区抓紧收获晾晒。"},
    "小雪": {"title": "❄️ 小雪，设施农业", "content": "小雪到，气温持续走低。大棚蔬菜注意保温防冻，及时覆盖保温被。"},
    "大雪": {"title": "❄️ 大雪，防雪灾", "content": "大雪到，雪量大增。大棚注意及时除雪，防止压塌。畜舍做好防寒保暖。"},
    "冬至": {"title": "🥟 冬至，数九寒天", "content": "冬至到，数九寒天开始。做好越冬作物的防冻管理，果树涂白防冻，冬小麦镇压保苗。"},
    "小寒": {"title": "❄️ 小寒，防冻保苗", "content": "小寒大寒，冻成一团。果树、冬小麦注意防冻，雪后及时清雪。温室大棚注意保温。"},
    "大寒": {"title": "❄️ 大寒，冬闲备耕", "content": "大寒到，最冷时节。冬闲时节正好备耕，计划来年种植安排，准备种子和肥料。"},
}



# ============================================================
# 节气：lunar_python 天文算法
# ============================================================

def get_solar_term(today: date | None = None) -> dict[str, str] | None:
    """判断今天是否为 24 节气，返回 {name, title, content}，否则返回 None。

    用 lunar_python 天文算法精确计算节气日期，不再用日期范围匹配。
    日期基于东八区 now_china()，避免服务器非东八区时区导致节气判断错位。
    """
    if today is None:
        from app.core.timezone import now_china
        today = now_china().date()
    try:
        from lunar_python import Solar
        solar = Solar.fromYmd(today.year, today.month, today.day)
        lunar = solar.getLunar()
        jie_qi = lunar.getJieQi()  # 当日节气名（如 "立秋"），非节气日返回 ""
    except ImportError:
        # lunar_python 未安装时降级：不推节气
        return None
    except Exception:
        return None

    if not jie_qi or jie_qi not in SOLAR_TERMS:
        return None

    cfg = SOLAR_TERMS[jie_qi]
    return {
        "name": jie_qi,
        "title": cfg["title"],
        "content": cfg["content"],
    }


# ============================================================
# 节气推送（6:00 定时任务调用）
# ============================================================

def create_solar_term_notifications(db, logger=None) -> int:
    """如果今天是 24 节气，为所有活跃农户创建节气通知（当年去重）。

    去重逻辑：每个节气每年对每个农户只推 1 次。
    rule_code 格式：solar_term:{节气名}:{年}，如 solar_term:立秋:2026
    """
    from app.models import User, Notification
    from app.core.timezone import now_china

    term = get_solar_term()
    if not term:
        if logger:
            logger.info("[推送Agent] 今日非节气日，跳过节气推送")
        return 0

    # 当年去重 rule_code
    now = now_china()
    dedup_code = f"solar_term:{term['name']}:{now.year}"

    # 查所有活跃农户（仅 role=1 农户，不推给管理员/专家）
    users = db.query(User).filter(User.role == 1, User.status == 1).all()

    created = 0
    for user in users:
        # 查今年是否已给该农户推过这个节气
        existing = db.query(Notification).filter(
            Notification.user_id == user.id,
            Notification.rule_code == dedup_code,
        ).first()
        if existing:
            continue

        db.add(Notification(
            user_id=user.id,
            type="solar_term",
            title=term["title"],
            content=term["content"],
            rule_code=dedup_code,
        ))
        created += 1

    if logger:
        logger.info(f"[推送Agent] 节气推送完成（{term['name']}），创建 {created} 条通知（当年去重）")
    return created


# ============================================================
# 天气预警推送（30 分钟轮询调用）
# ============================================================

# 注：和风 weatheralert API 的 location 参数只接受 "经度,纬度"，
# 不认高德 adcode；推送前由 adcode_to_location_sync() 转换。


def _get_pushed_warning_ids(db, user_id: int) -> set[str]:
    """查询当前已推送的预警 ID 集合（从 Redis 读取，回退到 MySQL 近 7 天记录）。

    预警 ID 存储格式：rule_code = warning:{预警ID前32位}
    用 7 天窗口而非"当天"，避免跨天持续预警被重复推送。
    """
    try:
        from app.core.redis import redis_client
        key = f"push:warning_ids:{user_id}"
        ids = redis_client.smembers(key)
        if ids:
            return {str(i) for i in ids}
    except Exception:
        pass
    # Redis 不可用时回退到查 MySQL 近 7 天记录
    from app.models import Notification
    from app.core.timezone import now_china
    from datetime import timedelta
    start = now_china() - timedelta(days=7)
    rows = db.query(Notification.rule_code).filter(
        Notification.user_id == user_id,
        Notification.rule_code.like("warning:%"),
        Notification.created_at >= start,
    ).all()
    return {r[0].split(":", 1)[1] for r in rows if r[0] and r[0].startswith("warning:")}


def _mark_warning_pushed(user_id: int, warning_id: str, ttl_seconds: int = 259200):
    """标记某预警已推送（Redis，72 小时 TTL，覆盖预警最长生命周期）。"""
    try:
        from app.core.redis import redis_client
        key = f"push:warning_ids:{user_id}"
        redis_client.sadd(key, warning_id[:32])
        redis_client.expire(key, ttl_seconds)
    except Exception:
        pass


def create_weather_push_notifications(db, logger=None) -> int:
    """轮询任务入口：为所有有位置的农户推送气象预警。

    返回创建的推送条数。
    """
    from app.models import User, Notification
    from app.services import qweather_client
    from app.api.location import adcode_to_location_sync

    if not qweather_client._is_configured():
        if logger:
            logger.warning("[推送Agent] 和风 API 未配置，跳过天气推送")
        return 0

    # 仅 role=1 农户（不推给管理员/专家），且有 adcode 才能查天气
    users: list[User] = (
        db.query(User)
        .filter(User.role == 1, User.adcode.isnot(None), User.adcode != "", User.status == 1)
        .all()
    )

    if not users:
        if logger:
            logger.info("[推送Agent] 没有有位置的农户，跳过天气推送")
        return 0

    # 按 adcode 分组，每组只调一次高德 district + 和风预警 API
    adcode_users: dict[str, list[User]] = {}
    for u in users:
        adcode_users.setdefault(str(u.adcode), []).append(u)

    warning_created = 0
    unique_warning_ids = set()

    for adcode, group in adcode_users.items():
        # 和风 API 只认经纬度（"经度,纬度"），adcode 必须先转坐标
        location = adcode_to_location_sync(adcode)
        if not location:
            if logger:
                logger.warning(f"[推送Agent] adcode={adcode} 转经纬度失败，跳过该组")
            continue

        # 查气象预警
        try:
            warnings = qweather_client.fetch_warnings(location)
        except Exception as e:
            if logger:
                logger.warning(f"[推送Agent] 查预警失败 adcode={adcode} location={location}: {e}")
            warnings = []

        for w in warnings:
            unique_warning_ids.add(w["id"])

        # 为该组每个农户生成通知
        for user in group:
            pushed_ids = _get_pushed_warning_ids(db, user.id)
            for w in warnings:
                wid = w["id"]
                if wid in pushed_ids:
                    continue  # 该预警已推过，跳过

                # 预警类型配置
                w_cfg = qweather_client.WARNING_TYPES.get(w["type"])
                if not w_cfg:
                    continue

                title = f"⚠️ {w['type']}{w['level']}色预警"
                content = w["text"] or f"{w['title']}，请关注最新气象信息，做好农事防护。"

                db.add(Notification(
                    user_id=user.id,
                    type="weather_alert",
                    title=title,
                    content=content,
                    rule_code=f"warning:{wid[:32]}",
                ))
                _mark_warning_pushed(user.id, wid)
                warning_created += 1

    if logger:
        logger.info(f"[推送Agent] 轮询推送完成：通知 {warning_created} 条（覆盖 {len(unique_warning_ids)} 条预警）")
    return warning_created


# ============================================================
# 入口函数
# ============================================================

def run_solar_term_push(logger=None) -> int:
    """6:00 定时任务入口：只推节气。返回创建的推送条数。"""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        count = create_solar_term_notifications(db, logger)
        db.commit()
        return count
    except Exception as e:
        db.rollback()
        if logger:
            logger.error(f"[推送Agent] 节气推送失败: {e}", exc_info=True)
        raise
    finally:
        db.close()


def run_weather_poll_push(logger=None) -> int:
    """30 分钟轮询入口：查气象预警。返回创建的推送条数。"""
    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        count = create_weather_push_notifications(db, logger)
        db.commit()
        return count
    except Exception as e:
        db.rollback()
        if logger:
            logger.error(f"[推送Agent] 天气轮询推送失败: {e}", exc_info=True)
        raise
    finally:
        db.close()
