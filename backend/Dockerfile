FROM python:3.11-slim

# 系统依赖（bcrypt/openpyxl/pymilvus 编译需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# 安装 uv（Python 包管理器）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 先拷依赖文件，利用 Docker 缓存
COPY pyproject.toml uv.lock ./

# 同步依赖（生产环境，不含 dev）
RUN uv sync --frozen --no-dev

# 拷贝源码
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY seed.py ./

# 创建上传目录
RUN mkdir -p uploads/ai_chat uploads/articles uploads/expert uploads/farmwork uploads/avatar

# BGE-M3 模型：启动时自动下载到 /app/backend/models/bge-m3
# （首次启动会慢几分钟，之后 Docker volume 缓存）
ENV BGE_M3_MODEL_PATH=backend/models/bge-m3
ENV HF_ENDPOINT=https://hf-mirror.com

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
