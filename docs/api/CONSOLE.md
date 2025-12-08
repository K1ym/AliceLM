# Console API

> Console API - 开发者监控面板

**Base Path**: `/api/v1/console`

---

## 概览

Console API 提供 Agent 执行日志查询、Eval 评测运行等开发者功能。

---

## 端点列表

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/agent-runs` | 获取执行日志列表 |
| GET | `/agent-runs/stats` | 获取执行统计 |
| GET | `/agent-runs/{id}` | 获取执行详情 |
| POST | `/eval/run-suite` | 运行评测套件 |
| POST | `/eval/run-default` | 运行默认评测 |
| GET | `/tools` | 获取工具列表 |

---

## GET /agent-runs

获取 Agent 执行日志列表。

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| scene | string | 否 | 按场景过滤 |
| limit | int | 否 | 返回数量，默认 50 |
| offset | int | 否 | 偏移量，默认 0 |

### 响应

```json
[
  {
    "id": "run_abc123",
    "tenant_id": "1",
    "user_id": null,
    "scene": "research",
    "query": "对比这三个视频的观点",
    "answer": "根据分析，这三个视频的观点主要有以下不同...",
    "success": true,
    "duration_ms": 3456,
    "started_at": "2024-12-05T10:00:00",
    "finished_at": "2024-12-05T10:00:03"
  }
]
```

---

## GET /agent-runs/stats

获取 Agent 执行统计。

### 响应

```json
{
  "total_runs": 150,
  "success_rate": 0.92,
  "avg_duration_ms": 2345,
  "scenes": {
    "chat": 80,
    "research": 50,
    "timeline": 20
  }
}
```

---

## GET /agent-runs/{id}

获取执行详情（包含完整步骤）。

### 响应

```json
{
  "id": "run_abc123",
  "tenant_id": "1",
  "user_id": null,
  "scene": "research",
  "query": "对比这三个视频的观点",
  "answer": "根据分析...",
  "success": true,
  "duration_ms": 3456,
  "started_at": "2024-12-05T10:00:00",
  "finished_at": "2024-12-05T10:00:03",
  "steps": [
    {
      "step_idx": 1,
      "thought": "需要先搜索相关视频",
      "tool_name": "search_videos",
      "tool_args": {"query": "..."},
      "observation": "找到 3 个相关结果"
    }
  ],
  "tool_traces": [
    {
      "tool": "search_videos",
      "duration_ms": 123,
      "success": true
    }
  ],
  "citations": [
    {"type": "video", "id": "123", "title": "..."}
  ],
  "extra_context": {}
}
```

---

## POST /eval/run-suite

运行自定义评测套件。

### 请求

```json
{
  "name": "custom_suite",
  "cases": [
    {
      "scene": "chat",
      "query": "什么是单例模式？",
      "expected_answer": null,
      "expected_keywords": ["单例", "实例", "全局"],
      "expected_tool_calls": []
    },
    {
      "scene": "research",
      "query": "对比视频中的观点",
      "expected_keywords": ["对比", "观点"],
      "expected_tool_calls": ["search_videos"]
    }
  ]
}
```

### 响应

```json
{
  "suite_id": "suite_xyz789",
  "suite_name": "custom_suite",
  "total_cases": 2,
  "passed_cases": 1,
  "failed_cases": 1,
  "avg_score": 0.75,
  "total_time_ms": 5678,
  "results": [
    {
      "case_id": "case_1",
      "success": true,
      "score": 1.0,
      "answer": "单例模式是...",
      "reasoning": "包含所有预期关键词",
      "tools_called": [],
      "execution_time_ms": 2345
    },
    {
      "case_id": "case_2",
      "success": false,
      "score": 0.5,
      "answer": "...",
      "reasoning": "缺少 search_videos 调用",
      "tools_called": ["web_search"],
      "execution_time_ms": 3333
    }
  ]
}
```

---

## POST /eval/run-default

运行默认评测套件。

### 响应

```json
{
  "suite_id": "suite_default_123",
  "suite_name": "default",
  "total_cases": 10,
  "passed_cases": 9,
  "failed_cases": 1,
  "avg_score": 0.90,
  "total_time_ms": 15000,
  "results": [...]
}
```

---

## GET /tools

获取可用工具列表。

### 响应

```json
{
  "tools": [
    {
      "name": "echo",
      "description": "回显输入内容",
      "dangerous": false,
      "enabled": true
    },
    {
      "name": "search_videos",
      "description": "搜索视频库",
      "dangerous": false,
      "enabled": true
    },
    {
      "name": "deep_web_research",
      "description": "深度网络研究",
      "dangerous": false,
      "enabled": true
    }
  ]
}
```

---

## 前端使用建议

### Agent 执行日志页面

```typescript
// 获取日志列表
const runs = await consoleApi.getAgentRuns({ scene: 'research', limit: 20 });

// 获取统计
const stats = await consoleApi.getStats();

// 查看详情
const detail = await consoleApi.getRunDetail(runId);
```

### Eval 评测页面

```typescript
// 运行默认评测
const result = await consoleApi.runDefaultEval();

// 显示结果
console.log(`通过率: ${result.passed_cases}/${result.total_cases}`);
console.log(`平均分: ${result.avg_score}`);
```
