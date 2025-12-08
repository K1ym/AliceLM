# Knowledge API

> 知识图谱 API - 概念关联和学习追踪

**Base Path**: `/api/v1/knowledge`

---

## 概览

Knowledge API 用于查询知识图谱、获取概念关联、以及学习进度追踪。

---

## 端点列表

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/graph` | 获取知识图谱 |
| GET | `/concepts/{concept}/videos` | 获取概念相关视频 |
| GET | `/concepts/{concept}/related` | 获取相关概念 |
| GET | `/learning/stats` | 获取学习统计 |
| GET | `/learning/weekly-report` | 获取周报 |
| GET | `/learning/review-suggestions` | 获取复习建议 |

---

## GET /graph

获取完整知识图谱。

### 响应

```json
{
  "nodes": [
    {
      "id": "concept_1",
      "label": "设计模式",
      "type": "concept",
      "weight": 5
    },
    {
      "id": "video_123",
      "label": "设计模式详解",
      "type": "video"
    }
  ],
  "edges": [
    {
      "source": "video_123",
      "target": "concept_1",
      "relation": "contains"
    },
    {
      "source": "concept_1",
      "target": "concept_2",
      "relation": "related"
    }
  ]
}
```

---

## GET /concepts/{concept}/videos

获取包含某概念的视频列表。

### 路径参数

| 参数 | 说明 |
|------|------|
| concept | 概念名称（URL 编码） |

### 响应

```json
[
  {
    "id": 123,
    "bvid": "BV1xx411c7mD",
    "title": "设计模式详解",
    "author": "UP主"
  },
  {
    "id": 456,
    "bvid": "BV1yy222c8mE",
    "title": "实战设计模式",
    "author": "另一个UP主"
  }
]
```

---

## GET /concepts/{concept}/related

获取相关概念。

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| limit | int | 否 | 返回数量，默认 10 |

### 响应

```json
[
  {
    "concept": "单例模式",
    "similarity": 0.85,
    "co_occurrence": 3
  },
  {
    "concept": "工厂模式",
    "similarity": 0.72,
    "co_occurrence": 2
  }
]
```

---

## GET /learning/stats

获取学习统计。

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| days | int | 否 | 统计天数，默认 7 |

### 响应

```json
{
  "total_videos": 42,
  "total_duration": 36000,
  "completed_videos": 38,
  "concepts_learned": 25,
  "videos_by_day": {
    "2024-12-01": 3,
    "2024-12-02": 5,
    "2024-12-03": 2
  },
  "top_authors": [
    {"author": "UP主A", "count": 10},
    {"author": "UP主B", "count": 8}
  ]
}
```

---

## GET /learning/weekly-report

获取周报。

### 响应

```json
{
  "week_start": "2024-12-02",
  "week_end": "2024-12-08",
  "highlights": [
    "本周学习了 12 个视频",
    "新掌握了 8 个概念",
    "最感兴趣的领域是设计模式"
  ],
  "stats": {
    "total_videos": 12,
    "total_duration": 7200,
    "concepts_learned": 8
  },
  "recommendations": [
    "建议复习「单例模式」相关内容",
    "可以探索「工厂模式」延伸主题"
  ]
}
```

---

## GET /learning/review-suggestions

获取复习建议（基于遗忘曲线）。

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| limit | int | 否 | 返回数量，默认 5 |

### 响应

```json
[
  {
    "video_id": 123,
    "title": "设计模式详解",
    "last_viewed": "2024-11-28",
    "urgency": "high",
    "reason": "距上次观看已过 7 天"
  },
  {
    "video_id": 456,
    "title": "实战设计模式",
    "last_viewed": "2024-12-01",
    "urgency": "medium",
    "reason": "包含重要概念「单例模式」"
  }
]
```

---

## 前端使用建议

### 知识图谱可视化

```typescript
import { ForceGraph2D } from 'react-force-graph';

const KnowledgeGraph = () => {
  const { data } = useQuery('graph', () => knowledgeApi.getGraph());
  
  return (
    <ForceGraph2D
      graphData={data}
      nodeLabel="label"
      nodeColor={node => node.type === 'concept' ? '#f59e0b' : '#3b82f6'}
      linkDirectionalArrowLength={6}
      onNodeClick={(node) => handleNodeClick(node)}
    />
  );
};
```

### 学习统计图表

```typescript
import { LineChart, BarChart } from 'recharts';

const LearningStats = () => {
  const { data } = useQuery('stats', () => knowledgeApi.getLearningStats(7));
  
  // 转换为图表数据
  const chartData = Object.entries(data.videos_by_day).map(([date, count]) => ({
    date,
    count,
  }));
  
  return <LineChart data={chartData} />;
};
```
