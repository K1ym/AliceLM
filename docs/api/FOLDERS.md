# Folders (收藏夹) API

## 端点概览

| Method | Endpoint | 说明 |
|--------|----------|------|
| GET | `/api/v1/folders` | 获取收藏夹列表 |
| POST | `/api/v1/folders` | 添加收藏夹 |
| DELETE | `/api/v1/folders/{id}` | 删除收藏夹 |
| POST | `/api/v1/folders/{id}/scan` | 触发扫描 |
| PATCH | `/api/v1/folders/{id}/toggle` | 启用/禁用 |

---

## GET /api/v1/folders

获取监控的收藏夹列表

### 响应

```json
[
  {
    "id": 1,
    "folder_id": "12345678",
    "folder_type": "favlist",
    "name": "我的收藏",
    "is_active": true,
    "video_count": 42,
    "last_scan_at": "2024-12-01T10:00:00"
  },
  {
    "id": 2,
    "folder_id": "87654321",
    "folder_type": "favlist",
    "name": "技术视频",
    "is_active": true,
    "video_count": 18,
    "last_scan_at": "2024-12-01T09:30:00"
  }
]
```

### 前端使用

```typescript
const { data: folders } = await foldersApi.list();

// 渲染收藏夹列表
folders.map(folder => (
  <FolderCard
    key={folder.id}
    name={folder.name}
    videoCount={folder.video_count}
    lastScan={folder.last_scan_at}
    isActive={folder.is_active}
    onScan={() => handleScan(folder.id)}
    onDelete={() => handleDelete(folder.id)}
    onToggle={() => handleToggle(folder.id)}
  />
));
```

---

## POST /api/v1/folders

添加收藏夹监控

### 请求

```json
{
  "folder_id": "12345678",
  "folder_type": "favlist"
}
```

**folder_type 可选值:**
- `favlist` - B站收藏夹
- `season` - 合集/系列
- `subscription` - 订阅

### 响应

```json
{
  "id": 3,
  "folder_id": "12345678",
  "folder_type": "favlist",
  "name": "新添加的收藏夹",
  "is_active": true,
  "video_count": 0,
  "last_scan_at": null
}
```

### 前端调用

```typescript
// 添加收藏夹
const handleAddFolder = async () => {
  try {
    await foldersApi.add(folderId, 'favlist');
    toast.success('收藏夹添加成功');
    refetchFolders();
  } catch (error) {
    if (error.response?.status === 409) {
      toast.error('该收藏夹已存在');
    } else {
      toast.error('添加失败，请检查收藏夹ID');
    }
  }
};
```

---

## POST /api/v1/folders/{id}/scan

手动触发收藏夹扫描

### 响应

```json
{
  "message": "扫描任务已启动",
  "new_videos": 3,
  "task_id": "scan_abc123"
}
```

### 前端使用

```typescript
const handleScan = async (folderId: number) => {
  setScanning(true);
  try {
    const { data } = await foldersApi.scan(folderId);
    toast.success(`发现 ${data.new_videos} 个新视频`);
    refetchVideos();
  } finally {
    setScanning(false);
  }
};
```

---

## PATCH /api/v1/folders/{id}/toggle

启用/禁用收藏夹监控

### 响应

```json
{
  "id": 1,
  "is_active": false,
  "message": "收藏夹监控已暂停"
}
```

---

## DELETE /api/v1/folders/{id}

删除收藏夹 (不会删除已导入的视频)

### 响应

```json
{
  "message": "收藏夹已删除"
}
```

---

## 如何获取收藏夹ID

### 方法1: 从URL获取

B站收藏夹URL格式:
```
https://space.bilibili.com/用户ID/favlist?fid=收藏夹ID
```

例如:
```
https://space.bilibili.com/123456/favlist?fid=12345678
                                          ↑
                                     收藏夹ID
```

### 方法2: 前端提取

```typescript
function extractFolderId(url: string): string | null {
  const match = url.match(/fid=(\d+)/);
  return match ? match[1] : null;
}

// 使用
const folderId = extractFolderId('https://space.bilibili.com/xxx/favlist?fid=12345678');
// 结果: "12345678"
```

---

## 收藏夹管理UI

```
┌─────────────────────────────────────────────────┐
│  收藏夹管理                          [+ 添加]   │
├─────────────────────────────────────────────────┤
│                                                 │
│  ╭─────────────────────────────────────────╮   │
│  │ 📁 我的收藏                              │   │
│  │    42 个视频 · 上次扫描: 2小时前          │   │
│  │                        [扫描] [⏸] [🗑]   │   │
│  ╰─────────────────────────────────────────╯   │
│                                                 │
│  ╭─────────────────────────────────────────╮   │
│  │ 📁 技术视频                   ⏸ 已暂停   │   │
│  │    18 个视频 · 上次扫描: 1天前            │   │
│  │                        [扫描] [▶] [🗑]   │   │
│  ╰─────────────────────────────────────────╯   │
│                                                 │
└─────────────────────────────────────────────────┘
```
