"""统一时区处理 - 东八区（北京时间）

项目所有时间统一存东八区 naive datetime（不带 tzinfo），
避免 MySQL DATETIME 字段类型与时区混淆问题。
"""
from datetime import datetime, timezone, timedelta

CHINA_TZ = timezone(timedelta(hours=8))


def now_china() -> datetime:
    """返回当前东八区时间（naive，不带 tzinfo，兼容 MySQL DATETIME 字段）"""
    return datetime.now(CHINA_TZ).replace(tzinfo=None)
