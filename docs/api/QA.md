# QA (问答) API

## 端点概览

| Method | Endpoint | 说明 |
|--------|----------|------|
| POST | `/api/v1/qa/ask` | 知识库问答 |
| POST | `/api/v1/qa/search` | 语义搜索 |
| POST | `/api/v1/qa/summarize` | 生成摘要 |

---

## POST /api/v1/qa/ask

基于知识库的RAG问答

### 请求

```json
{
  "question": "这个视频讲了什么？",
  "video_ids": [1, 2, 3]  // 可选，限定搜索范围
}
```

### 响应

```json
{
  "answer": "根据你收藏的视频，这个概念是指...",
  "sources": [
    {
      "video_id": 1,
      "title": "设计入门教程",
      "relevance": 0.92
    },
    {
      "video_id": 3,
      "title": "产品设计思维",
      "relevance": 0.85
    }
  ],
  "conversation_id": "conv_abc123"
}
```

### 前端调用

```typescript
// 全局问答
const { data } = await qaApi.ask('什么是设计思维？');

// 针对特定视频问答
const { data } = await qaApi.ask('这个视频的核心观点是什么？', [videoId]);
```

### 流式响应 (SSE)

对于长回答，支持流式输出:

```typescript
// 前端使用 EventSource
const eventSource = new EventSource(`/api/v1/qa/ask/stream?question=${encodeURIComponent(question)}`);

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'token') {
    // 追加文字
    setAnswer(prev => prev + data.content);
  } else if (data.type === 'sources') {
    // 显示引用
    setSources(data.sources);
  } else if (data.type === 'done') {
    eventSource.close();
  }
};
```

---

## POST /api/v1/qa/search

语义搜索视频片段

### 请求

```json
{
  "query": "设计思维",
  "top_k": 10
}
```

### 响应

```json
[
  {
    "video_id": 1,
    "title": "设计入门教程",
    "content": "...设计思维是一种以用户为中心的创新方法论...",
    "score": 0.95
  },
  {
    "video_id": 5,
    "title": "产品经理必修课",
    "content": "...运用设计思维可以帮助我们更好地理解用户需求...",
    "score": 0.88
  }
]
```

### 前端使用

```typescript
// 搜索
const results = await qaApi.search('设计思维', 5);

// 显示搜索结果
results.data.map(result => (
  <SearchResult
    key={result.video_id}
    title={result.title}
    content={result.content}
    score={result.score}
    onClick={() => navigateToVideo(result.video_id)}
  />
));
```

---

## POST /api/v1/qa/summarize

为视频生成/重新生成摘要

### 请求

```
POST /api/v1/qa/summarize?video_id=123
```

### 响应

```json
{
  "video_id": 123,
  "summary": "这个视频主要讲述了设计思维的核心理念...",
  "key_points": [
    "设计思维是以用户为中心的方法论",
    "包含五个核心阶段：共情、定义、构思、原型、测试",
    "强调快速迭代和用户反馈"
  ],
  "concepts": ["设计思维", "用户体验", "原型设计"]
}
```

---

## 引用卡片交互

当AI回答包含引用时，前端需要渲染可点击的引用卡片：

```tsx
function CitationCard({ source }: { source: QASource }) {
  return (
    <div 
      className="bg-neutral-50 rounded-lg p-3 cursor-pointer hover:bg-neutral-100"
      onClick={() => router.push(`/dashboard/video/${source.video_id}`)}
    >
      <div className="flex items-center justify-between">
        <span className="font-medium text-sm">{source.title}</span>
        <span className="text-xs text-neutral-400">
          相关度 {(source.relevance * 100).toFixed(0)}%
        </span>
      </div>
    </div>
  );
}
```

---

## 错误处理

| 错误码 | 说明 | 前端处理 |
|--------|------|----------|
| 400 | 问题为空或过长 | 显示输入验证错误 |
| 404 | 指定的视频不存在 | 提示视频已删除 |
| 500 | RAG服务异常 | 显示"服务暂时不可用，请稍后重试" |
| 503 | LLM API限流 | 显示倒计时重试 |
