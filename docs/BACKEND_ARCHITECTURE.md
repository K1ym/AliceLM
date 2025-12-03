# AliceLM 后端架构文档

> 版本: 1.0 | 更新: 2024-12

---

## 1. 架构概览

### 1.1 设计原则

| 原则 | 说明 | 现状 |
|------|------|------|
| **模块化** | 功能解耦，独立演进 | 已实现 (services/) |
| **可扩展** | Provider 抽象层 | 已实现 (asr/ai) |
| **分层架构** | Router → Service → Repository | 部分实现 |
| **配置驱动** | YAML/ENV 配置 | 已实现 |

### 1.2 当前结构

```
bili2text-main/
├── apps/
│   ├── api/                  # FastAPI 主应用
│   │   ├── main.py           # 入口
│   │   ├── routers/          # 路由层
│   │   │   ├── videos.py
│   │   │   ├── conversations.py
│   │   │   ├── auth.py
│   │   │   └── ...
│   │   └── dependencies.py   # 依赖注入
│   └── mcp/                  # MCP 服务器
│
├── services/                 # 业务服务层
│   ├── ai/                   # AI 服务
│   │   ├── summarizer.py     # 摘要生成
│   │   ├── tagger.py         # 标签提取
│   │   ├── recommender.py    # 推荐系统
│   │   └── context_compressor.py
│   ├── asr/                  # 语音识别
│   │   ├── base.py           # 抽象基类
│   │   ├── manager.py        # Provider 管理
│   │   ├── faster_whisper.py
│   │   └── api_provider.py
│   ├── downloader/           # 下载服务
│   ├── knowledge/            # 知识图谱
│   ├── processor/            # 处理管道
│   ├── scheduler/            # 任务调度
│   ├── watcher/              # 监控服务
│   └── notifier/             # 通知服务
│
├── packages/                 # 共享包
│   ├── db/                   # 数据库
│   ├── config/               # 配置
│   ├── queue/                # 队列
│   └── logging/              # 日志
│
└── data/                     # 数据存储
```

---

## 2. 分层架构

### 2.1 层级职责

```
┌─────────────────────────────────────────────────────────────┐
│                      Routers (路由层)                        │
│  HTTP 入口，参数验证，响应格式化                              │
├─────────────────────────────────────────────────────────────┤
│                      Services (服务层)                       │
│  业务逻辑，流程编排，事务管理                                 │
├─────────────────────────────────────────────────────────────┤
│                    Repositories (仓储层)                     │
│  数据访问，CRUD 操作，查询构建                               │
├─────────────────────────────────────────────────────────────┤
│                      Packages (基础设施)                     │
│  数据库，配置，日志，队列                                     │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 目标结构

```
apps/api/
├── main.py
├── routers/              # 路由层 (现有)
│   ├── videos.py
│   └── ...
├── services/             # 应用服务层 (新增)
│   ├── video_service.py
│   ├── chat_service.py
│   └── ...
├── repositories/         # 仓储层 (新增)
│   ├── video_repo.py
│   ├── conversation_repo.py
│   └── ...
├── schemas/              # Pydantic 模型
│   ├── video.py
│   └── ...
└── dependencies.py
```

---

## 3. 服务模块规范

### 3.1 Provider 模式 (已实现)

```python
# services/asr/base.py
from abc import ABC, abstractmethod

class ASRProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio_path: str) -> TranscriptResult:
        pass

# services/asr/faster_whisper.py
class FasterWhisperProvider(ASRProvider):
    async def transcribe(self, audio_path: str) -> TranscriptResult:
        # 实现
        pass

# services/asr/manager.py
class ASRManager:
    def get_provider(self, name: str) -> ASRProvider:
        # 根据配置返回对应 provider
        pass
```

### 3.2 服务层模式 (待实现)

```python
# apps/api/services/video_service.py
from services.processor import Pipeline
from apps.api.repositories import VideoRepository

class VideoService:
    def __init__(
        self,
        repo: VideoRepository,
        pipeline: Pipeline,
    ):
        self.repo = repo
        self.pipeline = pipeline

    async def import_video(self, url: str, user_id: int) -> Video:
        # 1. 验证 URL
        # 2. 创建记录
        # 3. 启动处理管道
        video = await self.repo.create(url=url, user_id=user_id)
        await self.pipeline.start(video.id)
        return video
```

---

## 4. API 规范

### 4.1 响应格式

```python
# 成功响应
{
    "data": {...},
    "meta": {
        "page": 1,
        "page_size": 20,
        "total": 100
    }
}

# 错误响应
{
    "error": {
        "code": "VIDEO_NOT_FOUND",
        "message": "Video with id 123 not found",
        "details": {}
    }
}
```

### 4.2 路由规范

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/videos` | 列表 |
| GET | `/videos/{id}` | 详情 |
| POST | `/videos` | 创建 |
| PUT | `/videos/{id}` | 更新 |
| DELETE | `/videos/{id}` | 删除 |
| GET | `/videos/{id}/transcript` | 子资源 |

---

## 5. 优化计划

### Phase 1: 分层重构

- [x] 创建 `apps/api/repositories/` 目录
- [x] 抽取 video_repo.py
- [x] 抽取 conversation_repo.py
- [x] 创建 `apps/api/services/` 目录
- [ ] 重构 routers 使用 service 层 (进行中)

### Phase 2: 统一错误处理

- [x] 创建自定义异常类 (exceptions.py)
- [x] 统一错误响应格式
- [x] 添加全局异常处理器 (error_handlers.py)

### Phase 3: 依赖注入优化

- [x] 使用 FastAPI Depends (deps.py)
- [x] 创建服务工厂
- [ ] 支持测试 Mock

### Phase 4: 文档完善

- [ ] OpenAPI Schema 完善
- [ ] API 版本管理
- [ ] 自动生成前端类型

---

## 6. 配置管理

### 6.1 配置结构

```yaml
# config/config.yaml
app:
  name: AliceLM
  debug: false

database:
  url: sqlite:///data/alicelm.db

asr:
  provider: faster_whisper
  model: large-v3

llm:
  endpoints:
    - name: openai
      base_url: https://api.openai.com/v1
      models: [gpt-4, gpt-3.5-turbo]
```

### 6.2 环境变量

```bash
ALICELM_DATABASE_URL=
ALICELM_ASR_PROVIDER=
ALICELM_LLM_API_KEY=
```

---

## 7. 测试规范

### 7.1 测试分层

```
tests/
├── unit/                 # 单元测试
│   ├── services/
│   └── repositories/
├── integration/          # 集成测试
│   └── api/
└── fixtures/             # 测试数据
```

### 7.2 测试覆盖目标

| 层级 | 覆盖率目标 |
|------|-----------|
| Repositories | 90% |
| Services | 80% |
| Routers | 70% |
