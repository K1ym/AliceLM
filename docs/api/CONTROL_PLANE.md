# ControlPlane API

> 控制平面 API - 提供模型/工具/Prompt 配置信息

**Base Path**: `/api/v1/control-plane`

---

## 概览

ControlPlane API 提供只读访问，用于：
- 查看可用模型配置
- 查看场景工具列表
- 查看 Prompt 配置
- Console/Settings 页面数据展示

---

## 端点列表

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/models` | 列出所有模型 profiles |
| GET | `/models/resolve` | 查看某任务实际使用的模型 |
| GET | `/tools` | 列出场景可用工具 |
| GET | `/prompts` | 列出 Prompt keys |
| GET | `/summary` | 控制平面状态摘要 |

---

## GET /models

列出所有模型 profiles。

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| kind | string | 否 | 过滤类型: `chat`/`embedding`/`asr` |

### 请求示例

```bash
# 获取所有模型
GET /api/v1/control-plane/models

# 按类型过滤
GET /api/v1/control-plane/models?kind=chat
```

### 响应示例

```json
{
  "profiles": [
    {
      "id": "alice.chat.main",
      "kind": "chat",
      "provider": "openai",
      "model": "gpt-4.1",
      "base_url": null
    },
    {
      "id": "alice.embed.default",
      "kind": "embedding",
      "provider": "openai",
      "model": "text-embedding-3-large",
      "base_url": null
    }
  ]
}
```

---

## GET /models/resolve

查看某任务类型实际使用的模型（含配置叠加后的结果）。

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| task_type | string | 是 | 任务类型: `chat`/`summary`/`embedding`/`asr` |
| user_id | int | 否 | 用户 ID（默认用当前用户） |

### 请求示例

```bash
GET /api/v1/control-plane/models/resolve?task_type=chat
```

### 响应示例

```json
{
  "task_type": "chat",
  "tenant_id": 1,
  "user_id": 123,
  "resolved": {
    "profile_id": "alice.chat.main",
    "kind": "chat",
    "provider": "openai",
    "model": "gpt-4.1",
    "base_url": "https://api.openai.com/v1",
    "api_key_masked": "sk-a****wxyz"
  }
}
```

---

## GET /tools

列出场景可用工具。

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| scene | string | 否 | 场景: `chat`/`research`/`video`/`console` |

### 请求示例

```bash
# 获取指定场景的工具
GET /api/v1/control-plane/tools?scene=research

# 获取所有场景的工具映射
GET /api/v1/control-plane/tools
```

### 响应示例（指定场景）

```json
{
  "scene": "research",
  "tools": [
    {
      "name": "calculator",
      "description": "基础计算",
      "dangerous": false,
      "enabled": true
    },
    {
      "name": "deep_web_research",
      "description": "多步深度网络搜索",
      "dangerous": false,
      "enabled": true
    }
  ]
}
```

### 响应示例（所有场景）

```json
{
  "scene": null,
  "tools": [],
  "all_scenes": {
    "chat": ["echo", "current_time", "calculator"],
    "research": ["echo", "web_search", "deep_web_research"],
    "video": ["get_video_summary", "search_videos"]
  }
}
```

---

## GET /prompts

列出 Prompt keys 及当前生效的文案。

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| key | string | 否 | 指定 key，不传返回全部 |

### 请求示例

```bash
# 获取所有 prompts
GET /api/v1/control-plane/prompts

# 获取指定 key
GET /api/v1/control-plane/prompts?key=alice.system.base
```

### 响应示例

```json
{
  "prompts": [
    {
      "key": "alice.system.base",
      "value": "你是 Alice，一位长期陪伴用户的 AI 助手...",
      "overridden": false
    },
    {
      "key": "alice.task.summary",
      "value": "你现在扮演总结助手...",
      "overridden": true
    }
  ]
}
```

> **注意**: `value` 超过 500 字符会被截断并添加 `...`

---

## GET /summary

控制平面状态摘要，用于 Console「Alice 当前状态」卡片。

### 请求示例

```bash
GET /api/v1/control-plane/summary
```

### 响应示例

```json
{
  "models": {
    "chat": {
      "profile_id": "alice.chat.main",
      "provider": "openai",
      "model": "gpt-4.1"
    },
    "embedding": {
      "profile_id": "alice.embed.default",
      "provider": "openai",
      "model": "text-embedding-3-large"
    },
    "summary": {
      "profile_id": "alice.chat.main",
      "provider": "openai",
      "model": "gpt-4.1"
    },
    "asr": {
      "error": "未配置"
    }
  },
  "scenes": {
    "chat": ["echo", "current_time", "calculator"],
    "research": ["echo", "web_search", "deep_web_research"],
    "video": ["get_video_summary", "search_videos"],
    "library": ["search_videos"],
    "console": ["echo"]
  },
  "prompts": [
    "alice.system.base",
    "alice.task.chat",
    "alice.task.summary",
    "alice.task.tagger"
  ]
}
```

---

## 前端使用建议

| 场景 | 推荐 API |
|------|----------|
| Settings - 模型配置 | `GET /models` + `GET /models/resolve` |
| Settings - Prompt 编辑 | `GET /prompts` |
| Console - Alice 状态卡片 | `GET /summary` |
| 开发者面板 - 工具列表 | `GET /tools` |

---

## 错误响应

### 401 Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

### 422 Validation Error

```json
{
  "detail": [
    {
      "loc": ["query", "task_type"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```
