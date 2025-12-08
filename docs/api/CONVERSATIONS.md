# Conversations API

> 对话管理 API - 管理用户与 Alice 的对话

**Base Path**: `/api/v1/conversations`

---

## 概览

Conversations API 用于管理用户的对话历史，支持创建、查询、删除对话，以及发送消息获取流式回复。

---

## 端点列表

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/` | 获取对话列表 |
| POST | `/` | 创建新对话 |
| GET | `/{id}` | 获取对话详情 |
| DELETE | `/{id}` | 删除对话 |
| POST | `/{id}/messages/stream` | 发送消息（流式回复） |

---

## GET /

获取当前用户的对话列表。

### 响应

```json
[
  {
    "id": 1,
    "title": "关于设计模式的讨论",
    "created_at": "2024-12-05T10:00:00",
    "updated_at": "2024-12-05T10:30:00",
    "message_count": 8
  },
  {
    "id": 2,
    "title": "新对话",
    "created_at": "2024-12-05T11:00:00",
    "updated_at": "2024-12-05T11:00:00",
    "message_count": 0
  }
]
```

---

## POST /

创建新对话。

### 响应

```json
{
  "id": 3,
  "title": null,
  "created_at": "2024-12-05T12:00:00",
  "updated_at": "2024-12-05T12:00:00",
  "message_count": 0
}
```

---

## GET /{id}

获取对话详情（包含消息列表）。

### 响应

```json
{
  "id": 1,
  "title": "关于设计模式的讨论",
  "created_at": "2024-12-05T10:00:00",
  "updated_at": "2024-12-05T10:30:00",
  "messages": [
    {
      "id": 1,
      "role": "user",
      "content": "什么是单例模式？",
      "sources": null,
      "created_at": "2024-12-05T10:00:00"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "单例模式是一种设计模式...",
      "sources": "[{\"type\": \"video\", \"id\": \"123\"}]",
      "created_at": "2024-12-05T10:00:05"
    }
  ]
}
```

---

## DELETE /{id}

删除对话。

### 响应

```json
{
  "message": "对话已删除",
  "id": 1
}
```

### 错误响应

```json
{
  "detail": "对话 #1 不存在"
}
```

---

## POST /{id}/messages/stream

发送消息并获取流式 AI 回复。

### 请求

```json
{
  "content": "帮我总结这个视频的核心观点"
}
```

### 响应

返回 `text/event-stream` 格式的流式响应：

```
data: {"type": "start", "message_id": 123}

data: {"type": "content", "delta": "这个视频"}

data: {"type": "content", "delta": "主要讲述了"}

data: {"type": "content", "delta": "三个核心观点："}

data: {"type": "sources", "sources": [{"type": "video", "id": "456", "title": "..."}]}

data: {"type": "done", "full_content": "这个视频主要讲述了三个核心观点：..."}
```

### 流事件类型

| type | 说明 |
|------|------|
| `start` | 开始生成，包含 message_id |
| `content` | 内容增量，包含 delta |
| `sources` | 引用来源 |
| `done` | 完成，包含完整内容 |
| `error` | 错误信息 |

---

## 前端使用建议

### 处理流式响应

```typescript
async function sendMessage(conversationId: number, content: string) {
  const response = await fetch(`/api/v1/conversations/${conversationId}/messages/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({ content }),
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  let fullContent = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        
        if (data.type === 'content') {
          fullContent += data.delta;
          // 更新 UI
          updateMessageContent(fullContent);
        } else if (data.type === 'sources') {
          // 显示引用来源
          updateSources(data.sources);
        }
      }
    }
  }
}
```

---

## 消息角色

| role | 说明 |
|------|------|
| `user` | 用户消息 |
| `assistant` | Alice 回复 |
| `system` | 系统消息 |
