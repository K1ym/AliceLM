# AliceLM

AI 驱动的 知识库，将信息转化为可检索、可对话的结构化知识。

## 功能特性

- **视频转写** - 自动下载B站视频并使用 ASR 转写为文字
- **AI 分析** - 提取核心要点、关键概念，生成结构化摘要
- **智能问答** - 基于视频内容进行 AI 对话，支持引用上下文
- **收藏夹监控** - 自动同步B站收藏夹，新视频自动处理
- **多端点支持** - 支持 OpenAI、DeepSeek、Ollama 等多种 LLM

## 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                      Frontend                           │
│                   Next.js + React                       │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                      Backend                            │
│                  FastAPI + SQLite                       │
├─────────────────────────────────────────────────────────┤
│  Services                                               │
│  ├── ASR (Faster-Whisper / API)                        │
│  ├── LLM (OpenAI / DeepSeek / Ollama)                  │
│  ├── Processor (视频处理流水线)                         │
│  └── Watcher (收藏夹监控)                               │
└─────────────────────────────────────────────────────────┘
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 20+
- FFmpeg

### 本地开发

```bash
# 1. 克隆项目
git clone <repo>
cd alicelm

# 2. 安装后端依赖
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. 安装前端依赖
cd apps/web
npm install

# 4. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 5. 启动后端
uvicorn apps.api.main:app --reload

# 6. 启动前端 (新终端)
cd apps/web
npm run dev
```

访问 http://localhost:3000

### Docker 部署

```bash
# 生产环境
docker compose -f docker-compose.prod.yml up -d
```

详见 [部署文档](docs/DEPLOYMENT.md)

## 项目结构

```
alicelm/
├── apps/
│   ├── api/          # FastAPI 后端
│   └── web/          # Next.js 前端
├── services/
│   ├── asr/          # 语音识别
│   ├── llm/          # 大语言模型
│   ├── processor/    # 视频处理
│   └── watcher/      # 收藏夹监控
├── packages/         # 共享包
├── config/           # 配置文件
└── docs/             # 文档
```

## 配置说明

主要环境变量：

| 变量 | 说明 | 示例 |
|------|------|------|
| `ALICE_LLM__API_KEY` | LLM API Key | `sk-xxx` |
| `ALICE_LLM__BASE_URL` | LLM API 地址 | `https://api.openai.com/v1` |
| `ALICE_BILI_SESSDATA` | B站 Cookie | 用于获取收藏夹 |
| `ALICE_ASR__PROVIDER` | ASR 提供商 | `groq_whisper` |

完整配置见 [.env.example](.env.example)

## 文档

- [部署指南](docs/DEPLOYMENT.md)
- [前端架构](docs/FRONTEND_ARCHITECTURE.md)
- [API 文档](http://localhost:8000/docs) (启动后访问)

## 许可证

MIT License
