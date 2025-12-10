# 配置项与运行说明

## 配置架构

```
config/base/default.yaml          # 基础配置（所有环境共享）
    ↓
config/{ALICE_ENV}/default.yaml   # 环境覆盖（dev/prod）
    ↓
config/local/default.yaml         # 本地敏感信息（不提交版本库）
    ↓
环境变量                           # 最高优先级（ALICE_* 前缀，双下划线嵌套）
```

**配置读取**: `packages/config/settings.py` 使用 Pydantic Settings，`get_config()` 为全局入口。

## 环境变量与配置项

### 应用/运行时

| 名称 | 作用 | 必填 | 默认值 |
|------|------|------|--------|
| `ALICE_ENV` | 选择配置目录 | 否 | `dev` |
| `ALICE_DEBUG` | 开启调试模式/API 文档 | 否 | `false`（dev 覆盖为 true） |
| `ALICE_SECRET_KEY` | 应用密钥/JWT 签名 | 生产必填 | `change-me-in-production` |
| `PUBLIC_HOST` | 追加 CORS 允许域 | 否 | 无 |
| `ALICE_AGENT_LOG_PATH` | Agent 日志目录 | 否 | `data/agent_logs` |

### 数据库/存储

| 名称 | 作用 | 必填 | 默认值 |
|------|------|------|--------|
| `ALICE_DB__URL` | SQLAlchemy 数据库 URL | 生产建议填 | `sqlite:///data/bili_learner.db` |
| `ALICE_DB__ECHO` | SQL 语句回显 | 否 | `false` |
| `ALICE_RAG__CHROMA_PERSIST_DIR` | ChromaDB 持久化目录 | 否 | `data/chroma` |

### LLM 服务

| 名称 | 作用 | 必填 | 默认值 |
|------|------|------|--------|
| `ALICE_LLM__API_KEY` | LLM API 密钥 | 必填（除本地 Ollama） | 空 |
| `ALICE_LLM__BASE_URL` | LLM API 地址 | 否 | `https://api.openai.com/v1` |
| `ALICE_LLM__MODEL` | 默认模型 | 否 | `gpt-4o-mini` |
| `ALICE_LLM__PROVIDER` | Provider 名称 | 否 | `openai` |
| `<PROVIDER>_API_KEY` | 控制平面兜底密钥 | 视模型 | 无 |
| `<PROVIDER>_BASE_URL` | 控制平面兜底地址 | 视模型 | 无 |

### ASR 语音识别

| 名称 | 作用 | 必填 | 默认值 |
|------|------|------|--------|
| `ALICE_ASR__PROVIDER` | ASR 提供商（⚠️ 配置 `groq_whisper` 会触发未知提供商错误） | 否 | `faster_whisper` |
| `ALICE_ASR__API_KEY` | API ASR 密钥 | ⚠️ 暂未使用（API 提供商尚未接入） | - |
| `ALICE_ASR__MODEL_SIZE` | 本地模型尺寸 | 否 | `medium` |
| `ALICE_ASR__DEVICE` | 运行设备 | 否 | `auto` |

**已实现 Provider**: `faster_whisper`, `whisper_local`

**⚠️ 未接入**（配置中提到但代码未注册）: `groq_whisper`, `openai_whisper`

### RAG 检索

| 名称 | 作用 | 必填 | 默认值 |
|------|------|------|--------|
| `ALICE_RAG__PROVIDER` | RAG 提供商 | 否 | `chroma` |
| `ALICE_RAG__BASE_URL` | RAGFlow 地址 | ragflow 时必填 | `http://localhost:9380` |
| `ALICE_RAG__API_KEY` | RAGFlow 密钥 | 需鉴权时填 | 空 |

### 搜索/网络

| 名称 | 作用 | 必填 | 默认值 |
|------|------|------|--------|
| `ALICE_SEARCH__PROVIDER` | 搜索提供商 | 否 | `mock` |
| `ALICE_SEARCH__TAVILY_API_KEY` | Tavily 密钥 | Tavily 时必填 | 空 |
| `ALICE_SEARCH__EXA_API_KEY` | Exa 密钥 | Exa 时必填 | 空 |
| `ALICE_ALLOWED_DOMAINS` | HTTP 请求白名单 | 否 | 空（屏蔽内网） |

**可选 Provider**: `tavily`, `duckduckgo`, `exa`, `mock`

### B站集成

| 名称 | 作用 | 必填 | 默认值 |
|------|------|------|--------|
| `ALICE_BILI_SESSDATA` | B站 SESSDATA Cookie | 收藏夹功能必填 | 空 |
| `ALICE_BILI__POLL_INTERVAL` | 轮询间隔（秒） | 否 | `300` |

### MCP 集成

| 名称 | 作用 | 必填 | 默认值 |
|------|------|------|--------|
| `ALICE_MCP__ENDPOINTS` | MCP 端点列表 `name:url` | 使用 MCP 时必填 | 空 |
| `ALICE_MCP__API_KEY_<name>` | 各端点密钥 | 视端点 | 空 |

### 通知服务

| 名称 | 作用 | 必填 | 默认值 |
|------|------|------|--------|
| `ALICE_WECHAT__ENABLED` | 启用企业微信 | 否 | `false` |
| `ALICE_WECHAT__WEBHOOK_URL` | 机器人 Webhook | 启用时必填 | 空 |
| `ALICE_WECHAT__CORP_ID` | 企业 ID | 企业微信时填 | 空 |
| `ALICE_WECHAT__AGENT_ID` | 应用 ID | 企业微信时填 | 空 |
| `ALICE_WECHAT__SECRET` | 应用密钥 | 企业微信时填 | 空 |

### 工具/安全

| 名称 | 作用 | 必填 | 默认值 |
|------|------|------|--------|
| `ALICE_SAFE_DIRECTORIES` | 文件工具允许目录 | 否 | `~/alice_workspace,/tmp/alice` |
| `ALICE_FILE_WRITE_ENABLED` | 允许文件写入 | 否 | `false` |
| `ALICE_UNSAFE_TOOLS_ENABLED` | 允许 Shell/Python REPL | 否 | `false` |

### 前端 (Next.js)

| 名称 | 作用 | 必填 | 默认值 |
|------|------|------|--------|
| `NEXT_PUBLIC_API_URL` | API 基地址 | 构建时必填 | `http://localhost:8000` |
| `NEXT_PUBLIC_API_STREAM_URL` | SSE/流式地址 | 构建时必填 | `http://localhost:8000` |

## 不同环境的配置差异

| 配置项 | dev | prod |
|--------|-----|------|
| `debug` | `true` | `false` |
| API 文档 | 启用 | 禁用 |
| 数据库 | SQLite 本地 | 建议 PostgreSQL |
| 日志级别 | DEBUG | INFO/WARNING |

### 配置文件

```
config/
├── base/
│   ├── default.yaml      # 基础配置
│   ├── models.yaml       # 模型档案 + task 映射
│   ├── services.yaml     # Provider 选择与实现映射
│   ├── tools.yaml        # 工具配置
│   └── prompts.yaml      # Prompt 模板
├── dev/
│   └── default.yaml      # debug: true
├── prod/
│   └── default.yaml      # debug: false
└── local/
    └── default.yaml      # 本地敏感信息（不提交）
```

## 启动步骤

### 本地开发（后端）

```bash
# 1. 环境准备
python --version  # 需要 3.10+
brew install ffmpeg  # macOS，或对应系统的安装方式

# 2. 安装依赖
pip install -e ".[dev]"
# 或
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env，填写必填项：
# - ALICE_LLM__API_KEY
# - ALICE_ASR__API_KEY（如用 Groq/OpenAI）
# - ALICE_BILI_SESSDATA（如用收藏夹）
# - ALICE_SECRET_KEY（生产环境）

# 4. 启动 API
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000

# 5. （可选）启动 Worker
python -m services.worker
```

### 本地开发（前端）

```bash
cd apps/web
npm install

# 配置环境变量
cp .env.local.example .env.local
# 编辑 NEXT_PUBLIC_API_URL 等

npm run dev  # 端口 3000
```

### Docker Compose（开发）

```bash
# 基础服务
docker compose up --build

# 包含 RAGFlow（需要 ≥8GB 内存）
docker compose --profile rag up --build
```

### Docker Compose（生产）

```bash
# 确保 .env 已配置
docker compose -f docker-compose.prod.yml up -d
```

### 单独构建镜像

```bash
# 开发镜像
docker build -t alicelm:dev -f Dockerfile .

# 生产镜像
docker build -t alicelm:prod -f Dockerfile.prod .
```

### 依赖服务准备

| 服务 | 本地开发 | Docker |
|------|----------|--------|
| SQLite | 自动创建 `data/` 目录 | 挂载 `./data` |
| ChromaDB | 自动创建 | 挂载 `./data/chroma` |
| Redis | 可选 | compose 自动启动 |
| RAGFlow | 可选 | `--profile rag` |
| FFmpeg | 需手动安装 | 镜像已包含 |

## 常见问题与排查建议

### 启动失败

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| `ALICE_LLM__API_KEY` 为空 | .env 未加载 | 检查 `printenv \| grep ALICE`，确认 compose 有 `env_file` |
| 数据库路径不一致 | base 用 `bili_learner.db`，compose 用 `alicelm.db` | 统一 `ALICE_DB__URL` |
| `ModuleNotFoundError: services.worker` | Worker 模块不存在 | 补齐模块或改用其他调度入口 |
| FFmpeg 缺失 | 音频转写失败 | `brew install ffmpeg` 或使用 Docker |

### 服务连接

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| RAGFlow 启动失败 | 内存不足 | 确保 ≥8GB，检查 `docker compose logs ragflow` |
| Redis 连接失败 | 服务未启动 | `docker compose up redis` |
| CORS 错误 | 域名不匹配 | 设置 `PUBLIC_HOST` |
| 前端 API 404 | URL 配置错误 | 检查 `NEXT_PUBLIC_API_URL` |

### 脚本执行

| 问题 | 原因 | 解决方案 |
|------|------|----------|
| 直接运行 `python scripts/...` 配置为空 | 未加载 .env | `export $(cat .env \| xargs)` 或用 `python-dotenv` |
| 迁移脚本失败 | 仅支持 SQLite | 检查数据库类型，备份后运行 |

### 调试技巧

```bash
# 检查环境变量
printenv | grep ALICE

# 检查配置加载
python -c "from packages.config import get_config; print(get_config())"

# 检查数据库连接
python -c "from packages.db import get_session; print(list(get_session()))"

# 查看 Docker 日志
docker compose logs -f api
docker compose logs -f worker
```
