"""应用配置"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 数据库 - MySQL（密码从 .env 注入，勿硬编码）
    DATABASE_URL: str = ""

    # Redis（开发环境可选，部分功能不可用）
    REDIS_URL: str = "redis://localhost:6379/0"

    # PostgreSQL（LangGraph checkpointer + langmem store）
    PG_URL: str = ""

    # JWT（密钥从 .env 注入，勿硬编码）
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 短信
    SMS_PROVIDER: str = "console"
    SMS_CODE_TTL_SECONDS: int = 300
    SMS_SEND_INTERVAL_SECONDS: int = 60
    SMS_HOURLY_LIMIT: int = 5
    SMS_DAILY_LIMIT: int = 10

    # 阿里云号码认证服务
    ALIYUN_ACCESS_KEY_ID: str = ""
    ALIYUN_ACCESS_KEY_SECRET: str = ""
    ALIYUN_SMS_ENDPOINT: str = "dypnsapi.aliyuncs.com"
    ALIYUN_SMS_SIGN_NAME: str = ""
    ALIYUN_SMS_SCHEME_NAME: str = ""
    ALIYUN_SMS_TEMPLATE_LOGIN: str = "100001"
    ALIYUN_SMS_TEMPLATE_REGISTER: str = "100001"
    ALIYUN_SMS_TEMPLATE_RESET: str = "100003"

    # 高德地图
    AMAP_API_KEY: str = ""              # Web 端 JS API key（前端定位用，此处仅备份记录）
    AMAP_SECURITY_KEY: str = ""         # Web 端 JS securityJsCode（前端用，此处仅备份记录）
    AMAP_WEB_SERVICE_KEY: str = ""      # Web 服务 key（后端 restapi.amap.com 调用 regeo/geo 用）

    # 和风天气（推送 Agent 用：分钟级降水 + 气象预警）
    QWEATHER_API_KEY: str = ""          # 控制台申请的 Key
    QWEATHER_API_HOST: str = ""         # 专属 API Host（形如 xxx.qweatherapi.com）；旧版可用 devapi.qweather.com

    # AI 知识问答
    QWEN_VL_API_KEY: str = ""
    QWEN_VL_BASE_URL: str = "https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
    QWEN_VL_MODEL: str = "qwen-vl-plus"
    VL_API_KEY: str = ""
    VL_BASE_URL: str = ""
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-v4-flash"
    TAVILY_API_KEY: str = ""
    AI_IMAGE_MAX_MB: int = 5
    AI_IMAGE_MAX_COUNT: int = 5

    # 病虫害 RAG
    BGE_M3_DEVICE: str = "cpu"
    BGE_M3_MODEL_PATH: str = ""
    EMBEDDING_DIM: int = 1024
    BGE_M3_BATCH_SIZE: int = 16
    BGE_M3_MAX_LENGTH: int = 1536
    MILVUS_HOST: str = "127.0.0.1"
    MILVUS_PORT: str = "19530"
    MILVUS_COLLECTION_PEST: str = "pest_knowledge"
    PEST_RAG_SCORE_THRESHOLD: float = 0.50
    PEST_RAG_TOP_K: int = 5

    # 服务
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://112.124.1.128",
    ]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
