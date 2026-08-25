FROM python:3.11-slim

# 换阿里云 debian 源（加速 apt）
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true && \
    sed -i 's|security.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|security.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true

# 系统依赖（bcrypt/openpyxl/pymilvus 编译需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# 用 pip 安装 uv（避免从 ghcr.io 拉 uv 镜像，国内极慢）
RUN pip install --index-url https://mirrors.aliyun.com/pypi/simple/ uv -i https://mirrors.aliyun.com/pypi/simple/

WORKDIR /app

# 先拷依赖文件，利用 Docker 缓存
COPY pyproject.toml uv.lock ./

# 创建 venv（--seed 安装 pip，用于装 torch）
RUN uv venv --seed .venv

# 导出依赖列表，移除 torch 行（单独装 CPU 版，避免下载2GB+ CUDA/nvidia包）
RUN uv export --no-hashes --no-dev -o requirements.txt && \
    sed -i '/^torch/d' requirements.txt

# 先单独装 PyTorch（--no-deps 跳过 nvidia/CUDA 依赖，只下 torch 本体 ~900MB）
# PyPI 上的 torch 是完整版，但 --no-deps 不拉 nvidia-*/triton 等几个 GB 的包
# torch 的非 CUDA 依赖（filelock/sympy 等）在后续 requirements.txt 步骤补上
RUN VIRTUAL_ENV=/app/.venv \
    /app/.venv/bin/pip install --no-cache-dir --timeout 600 --no-deps torch \
    --index-url https://mirrors.aliyun.com/pypi/simple/

# 装其他依赖（阿里云源加速，torch 已满足会跳过）
RUN UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/ \
    VIRTUAL_ENV=/app/.venv \
    uv pip install -r requirements.txt

# 拷贝源码
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY seed.py ./

# 创建上传目录
RUN mkdir -p uploads/ai_chat uploads/articles uploads/expert uploads/farmwork uploads/avatar

# BGE-M3 模型：启动时自动下载到 /app/backend/models/bge-m3
# 用 hf-mirror.com 镜像加速（HuggingFace 国内镜像）
ENV BGE_M3_MODEL_PATH=backend/models/bge-m3
ENV HF_ENDPOINT=https://hf-mirror.com

EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
