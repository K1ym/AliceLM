# 后端 API 与路由梳理

**文档生成时间**: 2025-12-08

**数据来源**: 代码仓库静态分析 (`apps/api/routers/*.py`)

---

## API 概览

### 版本与基础路径

| 版本 | 基础路径 | 说明 |
|------|----------|------|
| v1 | `/api/v1` | 当前唯一版本 |

### 模块分组

| 模块 | 路径前缀 | 文件 | 端点数 | 说明 |
|------|----------|------|--------|------|
| 认证 | `/api/v1/auth` | `auth.py` | 6 | 登录/注册/用户信息 |
| 视频 | `/api/v1/videos` | `videos.py` | 17 | 视频 CRUD 与处理队列 |
| 收藏夹 | `/api/v1/folders` | `folders.py` | 5 | 监控收藏夹管理 |
| 对话 | `/api/v1/conversations` | `conversations.py` | 5 | 智能对话 |
| 问答 | `/api/v1/qa` | `qa.py` | 3 | RAG 知识问答 |
| 知识图谱 | `/api/v1/knowledge` | `knowledge.py` | 6 | 学习统计与知识图谱 |
| 配置 | `/api/v1/config` | `config.py` | 10+ | 用户/模型配置 |
| B站绑定 | `/api/v1/bilibili` | `bilibili.py` | 6 | B站账号绑定 |
| 系统 | `/api/v1/system` | `system.py` | 2 | 存储统计与清理 |
| 灵感建议 | `/api/v1/suggestions` | `suggestions.py` | 1 | AI 灵感建议 |
| Agent | `/api/v1/agent` | `agent.py` | 3 | Agent 对话入口 |
| Console | `/api/v1/console` | `console.py` | 5 | 管理/观测/Eval |
| ControlPlane | `/api/v1/control-plane` | `control_plane.py` | 5 | 控制平面查询 |

---

## 接口总表

### 1. 认证模块 `/api/v1/auth`

| 方法 | 路径 | Handler | 功能 | 认证 |
|------|------|---------|------|------|
| `POST` | `/login` | `login()` | 用户登录 | ❌ 公开 |
| `POST` | `/register` | `register()` | 用户注册 | ❌ 公开 |
| `GET` | `/me` | `get_me()` | 获取当前用户信息 | ✅ JWT |
| `POST` | `/logout` | `logout()` | 登出 (客户端删除 Token) | ❌ 公开 |
| `PUT` | `/profile` | `update_profile()` | 更新个人信息 | ✅ JWT |
| `PUT` | `/password` | `change_password()` | 修改密码 | ✅ JWT |

**文件**: `apps/api/routers/auth.py`

---

### 2. 视频模块 `/api/v1/videos`

| 方法 | 路径 | Handler | 功能 | 认证 |
|------|------|---------|------|------|
| `POST` | `/` | `import_video()` | 导入单个视频 | ✅ Tenant |
| `POST` | `/batch` | `import_videos_batch()` | 批量导入 (最多20条) | ✅ Tenant |
| `GET` | `/` | `list_videos()` | 分页获取视频列表 | ✅ Tenant |
| `GET` | `/queue/list` | `get_processing_queue()` | 获取处理队列状态 | ✅ Tenant |
| `GET` | `/queue/info` | `get_queue_info()` | 获取并行队列信息 | ❌ 公开 |
| `GET` | `/{video_id}` | `get_video()` | 获取视频详情 | ✅ Tenant |
| `GET` | `/{video_id}/transcript` | `get_transcript()` | 获取转写文本 | ✅ Tenant |
| `DELETE` | `/{video_id}` | `delete_video()` | 删除视频 | ✅ Tenant |
| `POST` | `/{video_id}/reprocess` | `reprocess_video()` | 重新处理视频 | ✅ Tenant |
| `GET` | `/stats/summary` | `get_stats()` | 获取视频统计 | ✅ Tenant |
| `GET` | `/stats/tags` | `get_top_tags()` | 获取热门标签 | ✅ Tenant |
| `POST` | `/{video_id}/process` | `process_video_now()` | 立即开始处理 | ✅ User+Tenant |
| `GET` | `/{video_id}/status` | `get_video_status()` | 获取处理状态 | ✅ Tenant |
| `POST` | `/{video_id}/cancel` | `cancel_video_processing()` | 取消处理 | ✅ Tenant |
| `DELETE` | `/{video_id}/queue` | `remove_from_queue()` | 从队列移除 | ✅ Tenant |
| `GET` | `/{video_id}/comments` | `get_video_comments()` | 获取B站评论 | ✅ Tenant |

**文件**: `apps/api/routers/videos.py`

---

### 3. 收藏夹模块 `/api/v1/folders`

| 方法 | 路径 | Handler | 功能 | 认证 |
|------|------|---------|------|------|
| `GET` | `/` | `list_folders()` | 获取收藏夹列表 | ✅ Tenant |
| `POST` | `/` | `add_folder()` | 添加监控收藏夹 | ✅ User+Tenant |
| `DELETE` | `/{folder_id}` | `delete_folder()` | 删除收藏夹 | ✅ Tenant |
| `POST` | `/{folder_id}/scan` | `scan_folder()` | 立即扫描收藏夹 | ✅ User+Tenant |
| `PATCH` | `/{folder_id}/toggle` | `toggle_folder()` | 切换启用状态 | ✅ Tenant |

**文件**: `apps/api/routers/folders.py`

---

### 4. 对话模块 `/api/v1/conversations`

| 方法 | 路径 | Handler | 功能 | 认证 |
|------|------|---------|------|------|
| `GET` | `/` | `list_conversations()` | 获取对话列表 | ✅ User |
| `POST` | `/` | `create_conversation()` | 创建新对话 | ✅ User |
| `DELETE` | `/{conversation_id}` | `delete_conversation()` | 删除对话 | ✅ User |
| `GET` | `/{conversation_id}` | `get_conversation()` | 获取对话详情 | ✅ User |
| `POST` | `/{conversation_id}/messages/stream` | `send_message_stream()` | 发送消息 (SSE流式) | ✅ User |

**文件**: `apps/api/routers/conversations.py`

---

### 5. 问答模块 `/api/v1/qa`

| 方法 | 路径 | Handler | 功能 | 认证 |
|------|------|---------|------|------|
| `POST` | `/ask` | `ask_question()` | RAG 知识问答 | ✅ Tenant |
| `POST` | `/search` | `search_videos()` | 语义搜索 | ✅ Tenant |
| `POST` | `/summarize` | `summarize_video()` | 生成视频摘要 | ✅ Tenant |

**文件**: `apps/api/routers/qa.py`

---

### 6. 知识图谱模块 `/api/v1/knowledge`

| 方法 | 路径 | Handler | 功能 | 认证 |
|------|------|---------|------|------|
| `GET` | `/graph` | `get_knowledge_graph()` | 获取知识图谱 | ✅ Tenant |
| `GET` | `/concepts/{concept}/videos` | `get_concept_videos()` | 获取概念相关视频 | ✅ Tenant |
| `GET` | `/concepts/{concept}/related` | `get_related_concepts()` | 获取相关概念 | ✅ Tenant |
| `GET` | `/learning/stats` | `get_learning_stats()` | 获取学习统计 | ✅ User |
| `GET` | `/learning/weekly-report` | `get_weekly_report()` | 获取周报 | ✅ User |
| `GET` | `/learning/review-suggestions` | `get_review_suggestions()` | 获取复习建议 | ✅ User |

**文件**: `apps/api/routers/knowledge.py`

---

### 7. 配置模块 `/api/v1/config`

| 方法 | 路径 | Handler | 功能 | 认证 |
|------|------|---------|------|------|
| `GET` | `/` | `get_config()` | 获取完整配置 | ✅ User |
| `PUT` | `/asr` | `update_asr_config()` | 更新 ASR 配置 | ✅ User |
| `PUT` | `/llm` | `update_llm_config()` | 更新 LLM 配置 | ✅ User |
| `PUT` | `/notify` | `update_notify_config()` | 更新通知配置 | ✅ User |
| `GET` | `/llm/endpoints` | `list_llm_endpoints()` | 获取自定义 LLM 端点 | ✅ User |
| `POST` | `/llm/endpoints` | `add_llm_endpoint()` | 添加 LLM 端点 | ✅ User |
| `DELETE` | `/llm/endpoints/{id}` | `delete_llm_endpoint()` | 删除 LLM 端点 | ✅ User |
| `GET` | `/llm/endpoints/{id}/models` | `get_endpoint_models()` | 获取端点可用模型 | ✅ User |
| `PUT` | `/model-tasks` | `update_model_tasks()` | 更新任务模型配置 | ✅ User |
| `GET` | `/model-tasks` | `get_model_tasks()` | 获取任务模型配置 | ✅ User |
| `GET` | `/prompts` | `list_user_prompts()` | 获取用户 Prompt 配置 | ✅ User |
| `GET` | `/llm/models` | `list_available_models()` | 获取可用模型列表 | ✅ User |
| `GET` | `/asr/providers` | `list_asr_providers()` | 获取 ASR 服务商列表 | ✅ User |
| `GET` | `/llm/providers` | `list_llm_providers()` | 获取 LLM 服务商列表 | ✅ User |
| `GET` | `/llm/presets` | `list_llm_presets()` | 获取 LLM 预设配置 | ✅ User |

> ⚠️ **注意**: config.py 包含近 20 个端点，上表仅列出主要接口

**文件**: `apps/api/routers/config.py`

---

### 8. B站绑定模块 `/api/v1/bilibili`

| 方法 | 路径 | Handler | 功能 | 认证 |
|------|------|---------|------|------|
| `GET` | `/qrcode` | `generate_qrcode()` | 生成登录二维码 | ✅ User |
| `GET` | `/qrcode/poll` | `poll_qrcode()` | 轮询扫码状态 | ✅ User |
| `GET` | `/status` | `get_bind_status()` | 获取绑定状态 | ✅ User |
| `DELETE` | `/unbind` | `unbind_bilibili()` | 解绑B站账号 | ✅ User |
| `GET` | `/folders` | `get_bilibili_folders()` | 获取B站收藏夹 | ✅ User |
| `GET` | `/folders/{folder_type}/{folder_id}` | `get_folder_videos()` | 获取收藏夹视频 | ✅ User |

**文件**: `apps/api/routers/bilibili.py`

---

### 9. 系统模块 `/api/v1/system`

| 方法 | 路径 | Handler | 功能 | 认证 |
|------|------|---------|------|------|
| `GET` | `/storage` | `get_storage_stats()` | 获取存储统计 | ✅ User |
| `POST` | `/cleanup` | `cleanup_audio()` | 清理音频文件 | ✅ User |

**文件**: `apps/api/routers/system.py`

---

### 10. 灵感建议模块 `/api/v1/suggestions`

| 方法 | 路径 | Handler | 功能 | 认证 |
|------|------|---------|------|------|
| `GET` | `/` | `get_suggestions()` | 获取 AI 灵感建议 | ✅ User |

**文件**: `apps/api/routers/suggestions.py`

---

### 11. Agent 模块 `/api/v1/agent`

| 方法 | 路径 | Handler | 功能 | 认证 |
|------|------|---------|------|------|
| `POST` | `/chat` | `agent_chat()` | Agent 统一对话入口 | ✅ Tenant |
| `GET` | `/strategies` | `list_strategies()` | 列出支持的策略 | ❌ 公开 |
| `GET` | `/scenes` | `list_scenes()` | 列出支持的场景 | ❌ 公开 |

**文件**: `apps/api/routers/agent.py`

---

### 12. Console 模块 `/api/v1/console`

| 方法 | 路径 | Handler | 功能 | 认证 |
|------|------|---------|------|------|
| `GET` | `/agent-runs` | `list_agent_runs()` | 获取 Agent 执行日志 | ✅ Tenant |
| `GET` | `/agent-runs/stats` | `get_agent_run_stats()` | 获取执行统计 | ✅ Tenant |
| `GET` | `/agent-runs/{run_id}` | `get_agent_run_detail()` | 获取执行详情 | ✅ Tenant |
| `POST` | `/eval/run-suite` | `run_eval_suite()` | 运行 Eval 套件 | ✅ Tenant |
| `POST` | `/eval/run-default` | `run_default_eval()` | 运行默认 Eval | ✅ Tenant |
| `GET` | `/tools` | `list_tools()` | 列出可用工具 | ✅ Tenant |

**文件**: `apps/api/routers/console.py`

---

### 13. ControlPlane 模块 `/api/v1/control-plane`

| 方法 | 路径 | Handler | 功能 | 认证 |
|------|------|---------|------|------|
| `GET` | `/models` | `list_model_profiles()` | 列出模型 Profiles | ✅ User |
| `GET` | `/models/resolve` | `resolve_model_for_task()` | 解析任务实际使用的模型 | ✅ User |
| `GET` | `/tools` | `list_tools()` | 列出场景可用工具 | ✅ User |
| `GET` | `/prompts` | `list_prompts()` | 列出 Prompt Keys | ✅ User |
| `GET` | `/summary` | `get_control_plane_summary()` | 控制平面状态摘要 | ✅ User |

**文件**: `apps/api/routers/control_plane.py`

---

### 14. 全局端点

| 方法 | 路径 | Handler | 功能 | 认证 |
|------|------|---------|------|------|
| `GET` | `/health` | `health_check()` | 健康检查 | ❌ 公开 |
| `GET` | `/api/v1` | `api_info()` | API 信息 | ❌ 公开 |

**文件**: `apps/api/main.py`

---

## 关键接口详情

### 1. 视频导入 `POST /api/v1/videos`

**请求体**:
```json
{
  "url": "https://www.bilibili.com/video/BV1xx411c7mD",
  "auto_process": true
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `url` | string | ✅ | B站视频 URL 或 BV 号 |
| `auto_process` | boolean | ❌ | 是否自动处理 (默认 true) |

**响应** (新导入):
```json
{
  "id": 123,
  "source_type": "bilibili",
  "source_id": "BV1xx411c7mD",
  "title": "视频标题",
  "status": "pending",
  "message": "已加入处理队列"
}
```

**响应** (已存在):
```json
{
  "id": 123,
  "source_type": "bilibili",
  "source_id": "BV1xx411c7mD",
  "title": "视频标题",
  "status": "done",
  "message": "视频已存在"
}
```

---

### 2. Agent 对话 `POST /api/v1/agent/chat`

**请求体**:
```json
{
  "query": "这个视频讲了什么？",
  "scene": "chat",
  "video_id": 123,
  "conversation_id": null,
  "selection": null,
  "extra_context": {}
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | ✅ | 用户问题 |
| `scene` | string | ❌ | 场景 (chat/research/timeline/library/video/graph) |
| `video_id` | int | ❌ | 关联视频 ID |
| `conversation_id` | int | ❌ | 对话 ID |
| `selection` | string | ❌ | 用户选中的文本 |
| `extra_context` | object | ❌ | 额外上下文 |

**响应**:
```json
{
  "answer": "这个视频主要讲述了...",
  "citations": [
    { "type": "video", "id": "123", "title": "...", "snippet": "..." }
  ],
  "steps": [
    { "step_idx": 1, "thought": "...", "tool_name": "search_videos" }
  ],
  "strategy": "chat",
  "processing_time_ms": 1500
}
```

---

### 3. 发送消息 (SSE) `POST /api/v1/conversations/{id}/messages/stream`

**请求体**:
```json
{
  "content": "请解释一下这个概念"
}
```

**响应**: Server-Sent Events 流

```
data: {"type": "thinking", "content": "正在检索相关内容..."}
data: {"type": "content", "content": "这个"}
data: {"type": "content", "content": "概念"}
data: {"type": "content", "content": "是指..."}
data: {"type": "done", "sources": [...]}
```

---

### 4. RAG 问答 `POST /api/v1/qa/ask`

**请求体**:
```json
{
  "question": "什么是机器学习？",
  "video_ids": [1, 2, 3]
}
```

**响应**:
```json
{
  "answer": "机器学习是...",
  "sources": [
    { "video_id": 1, "title": "...", "relevance": 0.95 }
  ],
  "conversation_id": null
}
```

---

### 5. 登录 `POST /api/v1/auth/login`

**请求体**:
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

---

## 鉴权与权限控制

### 认证机制

| 组件 | 实现 | 文件位置 |
|------|------|----------|
| Token 类型 | JWT (HS256) | `apps/api/routers/auth.py:28-41` |
| 有效期 | 24 小时 | `apps/api/routers/auth.py:25` |
| 传输方式 | `Authorization: Bearer <token>` | `apps/api/deps.py:27` |
| 密码哈希 | bcrypt | `apps/api/services/auth_service.py` |

### 依赖注入层级

```
┌─────────────────────────────────────────────────────────────────┐
│                         依赖注入链                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   get_db()                                                      │
│       │                                                         │
│       └───► get_current_user(credentials, db)                   │
│                   │                                             │
│                   ├───► get_current_tenant(user, db)            │
│                   │                                             │
│                   └───► 各 Repository 依赖                       │
│                               │                                 │
│                               └───► 各 Service 依赖             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**文件**: `apps/api/deps.py`

### 认证级别

| 级别 | 依赖 | 返回值 | 说明 |
|------|------|--------|------|
| 公开 | 无 | - | 无需认证 |
| User | `get_current_user()` | `User` | 需要 JWT Token |
| Tenant | `get_current_tenant()` | `Tenant` | 需要 JWT + 租户隔离 |
| User+Tenant | 两者均依赖 | `User`, `Tenant` | 需要两者 |

### Debug 模式降级

```python
# apps/api/deps.py:47-52
if config.debug and credentials is None:
    user = db.query(User).filter(User.email == "admin@local").first()
    if user:
        return user
```

> ⚠️ **安全提示**: 开发模式下无 Token 时会自动使用 `admin@local` 用户

### 敏感操作接口

| 接口 | 风险级别 | 说明 |
|------|----------|------|
| `POST /api/v1/system/cleanup` | 🔴 高 | 删除文件 |
| `DELETE /api/v1/videos/{id}` | 🟡 中 | 删除视频数据 |
| `PUT /api/v1/auth/password` | 🟡 中 | 修改密码 |
| `DELETE /api/v1/bilibili/unbind` | 🟡 中 | 解绑账号 |
| `POST /api/v1/console/eval/*` | 🟡 中 | 执行 Agent 评测 |

---

## 错误处理

### 异常处理器注册

```python
# apps/api/main.py:42
register_exception_handlers(app)
```

### 常见错误码

| HTTP 状态码 | 含义 | 场景 |
|-------------|------|------|
| `400` | Bad Request | 参数校验失败、业务规则违反 |
| `401` | Unauthorized | 未提供 Token、Token 无效/过期 |
| `403` | Forbidden | 无权限访问资源 |
| `404` | Not Found | 资源不存在 |
| `422` | Unprocessable Entity | Pydantic 校验失败 |
| `500` | Internal Server Error | 服务异常 |

### 自定义异常

| 异常类 | 文件 | 说明 |
|--------|------|------|
| `NotFoundException` | `apps/api/exceptions.py` | 资源不存在 |
| `ValidationException` | `apps/api/exceptions.py` | 业务校验失败 |

---

## 发现的问题 / 待确认事项

### 🔴 安全问题

#### 1. Debug 模式无认证降级

| 问题 | 开发模式下无 Token 可直接使用 admin 用户 |
|------|-------------------------------------------|
| 位置 | `apps/api/deps.py:47-52` |
| 影响 | 若生产环境误开 debug，存在越权风险 |
| 建议 | 添加环境变量双重检查，或移除此逻辑 |

---

#### 2. `/queue/info` 无认证

| 问题 | 获取处理队列信息无需认证 |
|------|---------------------------|
| 位置 | `apps/api/routers/videos.py:208-212` |
| 影响 | 可能泄露系统负载信息 |
| 建议 | 添加 `get_current_user` 依赖 |

---

### 🟡 设计问题

#### 3. 角色权限未实现

| 问题 | 所有接口仅检查登录，不检查角色 |
|------|--------------------------------|
| 位置 | 所有 router 文件 |
| 影响 | OWNER/ADMIN/MEMBER/VIEWER 无区分 |
| 建议 | 添加 role-based 中间件或装饰器 |

---

#### 4. Console 接口无管理员鉴权

| 问题 | Console 接口标注"仅限管理员"但实际无检查 |
|------|-------------------------------------------|
| 位置 | `apps/api/routers/console.py:1-6` |
| 影响 | 普通用户可访问管理功能 |
| 建议 | 添加角色检查依赖 |

---

### 🟢 改进建议

#### 5. 缺少 API 限流

| 问题 | 无请求频率限制 |
|------|----------------|
| 影响 | 可能被恶意请求攻击 |
| 建议 | 使用 `slowapi` 或 Redis 限流 |

---

#### 6. 缺少请求日志中间件

| 问题 | 无统一的请求/响应日志记录 |
|------|---------------------------|
| 影响 | 难以追踪问题 |
| 建议 | 添加请求日志中间件 |

---

## 附录

### A. Swagger/OpenAPI

- 开发模式: `http://localhost:8000/docs` (Swagger UI)
- 开发模式: `http://localhost:8000/redoc` (ReDoc)
- 生产模式: 已禁用

**控制逻辑**:
```python
# apps/api/main.py:37-38
docs_url="/docs" if app_config.debug else None,
redoc_url="/redoc" if app_config.debug else None,
```

### B. CORS 配置

```python
# apps/api/main.py:47-54
_cors_origins = [
    "http://localhost:3000", "http://127.0.0.1:3000",
    "http://localhost:3002", "http://127.0.0.1:3002",
    "http://124.70.75.139:3000",  # frp 公网
]
```

- 开发模式: 动态匹配 `localhost/127.0.0.1:*`
- 生产模式: 仅允许白名单

---

*本文档由 AI 自动生成，基于代码仓库静态分析*
