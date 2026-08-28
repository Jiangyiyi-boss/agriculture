# 慧农宝（HuiNongBao）

面向农户的农业智能助手，提供作物病虫害诊断、个性种植推荐、农事安排、农业资讯等服务。

## 技术栈

| 模块 | 技术栈 |
|------|------|
| 前端 | Vue 3 + TypeScript + Element Plus + Pinia + Vue Router |
| 后端 | FastAPI + SQLAlchemy + PyMySQL + Redis |
| AI Agent | LangGraph ReAct + DeepSeek + Qwen-VL |
| 向量检索 | Milvus + BGE-M3 |
| 记忆系统 | PostgreSQL（LangGraph checkpointer + langmem store） |
| 部署 | Docker Compose |

## 功能

- **AI 智能问答**：ReAct Agent 自主调用 4 个工具（知识库检索、联网搜索、图片识别、种植规则引擎），支持多轮对话、短期记忆压缩、断点续传
- **病虫害诊断**：上传图片 → Qwen-VL 识别 → 知识库交叉验证 → 给出诊断和防治方案
- **种植推荐**：根据地区+土壤+月份，匹配适配作物和丰产参考亩产
- **农事安排**：农事作业计划管理（增删改查）
- **农业资讯**：专家/管理员发布的文章浏览
- **用户体系**：手机号注册登录、农户/专家/管理员三端

## 项目结构

```
├── backend/                  # 后端
│   ├── app/
│   │   ├── agents/graph/     # LangGraph ReAct Agent + 工具
│   │   ├── api/              # FastAPI 路由
│   │   ├── core/             # 配置、数据库、安全
│   │   ├── rag/              # 向量检索（BGE-M3 + Milvus）
│   │   ├── services/         # 短信、天气、推送
│   │   └── main.py           # 入口
│   ├── scripts/              # 数据导入脚本
│   ├── seed.py               # 初始数据
│   ├── pyproject.toml        # 依赖（uv 管理）
│   └── Dockerfile
├── frontend/                 # 前端
│   ├── src/
│   │   ├── api/              # Axios 封装
│   │   ├── layouts/          # 农户/管理员布局
│   │   ├── router/           # 路由
│   │   ├── stores/           # Pinia 状态管理
│   │   └── views/            # 页面
│   ├── nginx.conf            # Nginx 配置
│   ├── package.json
│   └── Dockerfile
├── data/                     # 知识库原始数据（Excel）
│   ├── plant/illness/        # 病害数据（70+ 种作物）
│   ├── plant/insect/         # 虫害数据
│   └── soil/                 # 土壤+作物适宜性数据
├── deploy/                   # Milvus 配置
├── docker-compose.yml
└── .env.example              # 环境变量模板
```

## 快速开始

### 1. 环境准备

- Docker 20+ & Docker Compose
- BGE-M3 模型文件（约 2GB，从 [HuggingFace](https://huggingface.co/BAAI/bge-m3) 下载，放置于项目根目录 `bge-m3/` 下，Docker 会挂载进容器）

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填写真实值
```

必填项：
- `MYSQL_ROOT_PASSWORD` — MySQL 密码
- `PG_PASSWORD` — PostgreSQL 密码
- `SECRET_KEY` — JWT 密钥
- `DEEPSEEK_API_KEY` — DeepSeek API Key
- `QWEN_VL_API_KEY` — Qwen-VL 图片识别 API Key
- `TAVILY_API_KEY` — 联网搜索 API Key
- `VITE_AMAP_WEB_KEY` / `VITE_AMAP_SECURITY_CODE` — 高德地图（前端定位用）
- `AMAP_WEB_SERVICE_KEY` — 高德 Web 服务 Key（后端逆地理编码用）
- `QWEATHER_API_KEY` / `QWEATHER_API_HOST` — 和风天气（天气预警推送用，Key 认证 + Host 调用地址）

### 3. 启动服务

```bash
docker compose up -d --build
```

服务启动后：
- 前端：`http://localhost`
- 后端 API：`http://localhost:8000/docs`
- MySQL：3306 / Redis：6379 / PostgreSQL：5432 / Milvus：19530

### 4. 导入知识库数据

首次部署需要将 `data/` 下的 Excel 导入 Milvus：

```bash
docker exec -it huinongbao-backend python scripts/import_pest_knowledge.py
docker exec -it huinongbao-backend python scripts/import_planting_data.py
```

## 本地开发

### 前端

```bash
cd frontend
pnpm install
pnpm dev
```

### 后端

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

## 环境变量说明

详见 [.env.example](.env.example)，所有敏感配置（数据库密码、API Key、JWT 密钥）均通过环境变量注入，不在代码中硬编码。
