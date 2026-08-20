"""Redis 连接"""

import redis

from app.core.config import settings

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


def get_redis():
    """FastAPI 依赖注入"""
    try:
        yield redis_client
    finally:
        pass