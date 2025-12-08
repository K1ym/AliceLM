# Agent API

> Agent 对话 API - Alice 智能体统一入口

**Base Path**: `/api/v1/agent`

---

## 概览

Agent API 是 Alice 智能体的统一入口，所有对话请求都通过此接口。
根据 `scene` 参数自动选择合适的策略（Chat/Research/Timeline）。

---

## 端点列表

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/chat` | Agent 对话 |
| GET | `/strategies` | 列出支持的策略 |
| GET | `/scenes` | 列出支持的场景 |

---

## POST /chat

Agent 统一对话入口。

### 请求

```json
{
  "query": "这个视频主要讲了什么？",
  "scene": "video",
  "video_id": 123,
  "conversation_id": 456,
  "selection": null,
  "extra_context": {}
}
```

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| query | string | ✅ | 用户问题 |
| scene | string | 否 | 场景，默认 `chat` |
| video_id | int | 否 | 关联视频 ID |
| conversation_id | int | 否 | 对话 ID |
| selection | string | 否 | 用户选中的文本 |
| extra_context | object | 否 | 额外上下文 |

### 场景 (scene) 选项

| 值 | 说明 | 策略 |
|----|------|------|
| `chat` | 日常对话（默认） | ChatStrategy |
| `research` | 深度研究 | ResearchStrategy |
| `timeline` | 时间线分析 | TimelineStrategy |
| `library` | 视频库查询 | ChatStrategy |
| `video` | 单视频问答 | ChatStrategy |
| `graph` | 知识图谱 | ChatStrategy |

### 响应

```json
{
  "answer": "这个视频主要讲述了...",
  "citations": [
    {
      "type": "video",
      "id": "123",
      "title": "视频标题",
      "snippet": "相关片段...",
      "url": null
    }
  ],
  "steps": [
    {
      "step_idx": 1,
      "thought": "需要搜索相关视频内容",
      "tool_name": "search_videos",
      "tool_args": {"query": "..."},
      "observation": "找到 3 个相关结果",
      "error": null
    }
  ],
  "strategy": "video",
  "processing_time_ms": 1234
}
```

---

## GET /strategies

列出支持的策略及其可用工具。

### 响应

```json
{
  "strategies": [
    {
      "name": "chat",
      "description": "对话策略 - 日常对话、解释和轻量问答",
      "allowed_tools": ["echo", "current_time", "get_video_summary"]
    },
    {
      "name": "research",
      "description": "研究策略 - 深度检索、多轮推理、Web 搜索",
      "allowed_tools": ["search_videos", "web_search", "deep_web_research"]
    },
    {
      "name": "timeline",
      "description": "时间线策略 - 学习轨迹、自我变化分析",
      "allowed_tools": ["get_timeline_summary", "get_learning_stats"]
    }
  ]
}
```

---

## GET /scenes

列出支持的场景。

### 响应

```json
{
  "scenes": [
    {"value": "chat", "name": "CHAT"},
    {"value": "research", "name": "RESEARCH"},
    {"value": "timeline", "name": "TIMELINE"},
    {"value": "library", "name": "LIBRARY"},
    {"value": "video", "name": "VIDEO"},
    {"value": "graph", "name": "GRAPH"},
    {"value": "tasks", "name": "TASKS"},
    {"value": "console", "name": "CONSOLE"}
  ]
}
```

---

## 前端使用建议

```typescript
// 基础对话
const response = await agentApi.chat({
  query: "帮我总结今天学了什么",
  scene: "timeline"
});

// 视频问答
const response = await agentApi.chat({
  query: "这个概念是什么意思？",
  scene: "video",
  video_id: 123,
  selection: "选中的文本片段"
});

// 深度研究
const response = await agentApi.chat({
  query: "对比这三个视频的观点",
  scene: "research"
});
```

---

## 错误响应

### 500 Internal Server Error

```json
{
  "detail": "Agent 执行失败: 具体错误信息"
}
```
