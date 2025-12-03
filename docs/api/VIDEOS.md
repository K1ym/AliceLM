# Videos API

## 视频存储策略

后端处理流程：
1. 下载B站视频
2. 提取音频文件 (保留)
3. 删除原视频 (节省空间)
4. 转写 + AI分析

**前端观看视频**: 使用B站嵌入播放器，无需本地存储

---

## 端点概览

| Method | Endpoint | 说明 |
|--------|----------|------|
| GET | `/api/v1/videos` | 获取视频列表 |
| GET | `/api/v1/videos/{id}` | 获取视频详情 |
| GET | `/api/v1/videos/{id}/transcript` | 获取转写文本 |
| POST | `/api/v1/videos` | 导入视频 |
| POST | `/api/v1/videos/{id}/reprocess` | 重新处理 |
| DELETE | `/api/v1/videos/{id}` | 删除视频 |
| GET | `/api/v1/videos/stats/summary` | 获取统计 |

---

## GET /api/v1/videos

获取视频列表 (分页)

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认 1 |
| page_size | int | 否 | 每页数量，默认 20，最大 100 |
| status | string | 否 | 状态筛选: pending/processing/done/failed |
| search | string | 否 | 搜索关键词 (标题) |

### 响应

```json
{
  "total": 42,
  "page": 1,
  "page_size": 20,
  "pages": 3,
  "items": [
    {
      "id": 1,
      "bvid": "BV1xx411c7mD",
      "title": "视频标题",
      "author": "UP主名称",
      "duration": 754,
      "cover_url": "https://...",
      "status": "done",
      "summary": "这个视频主要讲述了...",
      "created_at": "2024-12-01T10:00:00",
      "processed_at": "2024-12-01T10:05:00"
    }
  ]
}
```

### 前端调用

```typescript
const { data } = await videosApi.list({
  page: 1,
  page_size: 20,
  status: 'done',
  search: '设计'
});
```

---

## GET /api/v1/videos/{id}

获取视频详情

### 响应

```json
{
  "id": 1,
  "bvid": "BV1xx411c7mD",
  "title": "视频标题",
  "author": "UP主名称",
  "duration": 754,
  "cover_url": "https://...",
  "status": "done",
  "summary": "这个视频主要讲述了...",
  "key_points": [
    "第一个要点",
    "第二个要点",
    "第三个要点"
  ],
  "concepts": ["概念A", "概念B"],
  "tags": ["设计", "产品"],
  "transcript_path": "data/transcripts/BV1xx411c7mD.txt",
  "error_message": null,
  "created_at": "2024-12-01T10:00:00",
  "processed_at": "2024-12-01T10:05:00"
}
```

---

## GET /api/v1/videos/{id}/transcript

获取转写文本

### 响应

```json
{
  "bvid": "BV1xx411c7mD",
  "title": "视频标题",
  "transcript": "完整的转写文本...",
  "segments": [
    {
      "start": 0.0,
      "end": 5.2,
      "text": "大家好，今天我们来讲..."
    },
    {
      "start": 5.2,
      "end": 12.8,
      "text": "首先第一个概念是..."
    }
  ]
}
```

### 前端使用

```typescript
// 获取转写
const { data } = await videosApi.getTranscript(videoId);

// 渲染带时间戳的转写
data.segments.map(seg => (
  <div key={seg.start} onClick={() => seekTo(seg.start)}>
    <span className="text-neutral-400">[{formatTime(seg.start)}]</span>
    <span>{seg.text}</span>
  </div>
));
```

---

## POST /api/v1/videos

导入视频

### 请求

```json
{
  "bvid": "BV1xx411c7mD",
  "title": "视频标题",
  "author": "UP主",
  "duration": 754,
  "cover_url": "https://..."
}
```

### 响应

```json
{
  "id": 123,
  "status": "pending",
  "message": "视频已加入处理队列"
}
```

---

## GET /api/v1/videos/stats/summary

获取视频统计

### 响应

```json
{
  "total": 42,
  "done": 38,
  "pending": 2,
  "processing": 1,
  "failed": 1
}
```

### 前端使用

```typescript
const { data: stats } = await videosApi.stats();

// 显示状态筛选 Tab
<Tab label={`全部 (${stats.total})`} />
<Tab label={`已就绪 (${stats.done})`} />
<Tab label={`处理中 (${stats.processing + stats.pending})`} />
<Tab label={`失败 (${stats.failed})`} />
```

---

## 视频状态流转

```
pending → processing → done
                   ↘ failed → (reprocess) → pending
```

| 状态 | 说明 | UI显示 |
|------|------|--------|
| pending | 等待处理 | 灰色 + "等待处理" |
| processing | 处理中 | 动画 + 进度条 |
| done | 完成 | 正常显示 |
| failed | **失败** | 红色警告 + 重试按钮 |

---

## 前端视频播放

后端不存储视频文件，前端通过B站嵌入播放器观看：

### 嵌入播放器

```tsx
interface BilibiliPlayerProps {
  bvid: string;
  startTime?: number;  // 跳转到指定时间 (秒)
}

function BilibiliPlayer({ bvid, startTime }: BilibiliPlayerProps) {
  const src = startTime
    ? `//player.bilibili.com/player.html?bvid=${bvid}&t=${startTime}&autoplay=0`
    : `//player.bilibili.com/player.html?bvid=${bvid}&autoplay=0`;
  
  return (
    <iframe
      src={src}
      className="w-full aspect-video rounded-xl"
      allowFullScreen
      sandbox="allow-scripts allow-same-origin allow-popups"
    />
  );
}
```

### 时间戳跳转

点击转写文本的时间戳时，可以跳转到视频对应位置：

```tsx
function TranscriptLine({ segment, bvid }: { segment: Segment; bvid: string }) {
  const handleClick = () => {
    // 方式1: 更新iframe src
    const iframe = document.querySelector('iframe');
    if (iframe) {
      iframe.src = `//player.bilibili.com/player.html?bvid=${bvid}&t=${segment.start}&autoplay=1`;
    }
    
    // 方式2: 使用 postMessage (需要B站播放器支持)
    // iframe.contentWindow.postMessage({ action: 'seek', time: segment.start }, '*');
  };
  
  return (
    <div onClick={handleClick} className="cursor-pointer hover:bg-neutral-50 p-2 rounded">
      <span className="text-neutral-400 text-xs mr-2">[{formatTime(segment.start)}]</span>
      <span>{segment.text}</span>
    </div>
  );
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}
```

### 备用方案：跳转到B站

如果嵌入播放器有问题，可以直接跳转：

```tsx
function OpenInBilibili({ bvid, startTime }: { bvid: string; startTime?: number }) {
  const url = startTime
    ? `https://www.bilibili.com/video/${bvid}?t=${startTime}`
    : `https://www.bilibili.com/video/${bvid}`;
  
  return (
    <a 
      href={url} 
      target="_blank" 
      rel="noopener noreferrer"
      className="text-sm text-neutral-500 hover:text-neutral-900"
    >
      在B站打开
    </a>
  );
}
