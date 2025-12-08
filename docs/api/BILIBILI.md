# Bilibili API

> B站账号绑定 API - 管理 B站账号绑定和收藏夹

**Base Path**: `/api/v1/bilibili`

---

## 概览

Bilibili API 用于绑定用户的 B站账号，获取收藏夹列表，以便导入视频到 AliceLM。

---

## 端点列表

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/qrcode` | 生成登录二维码 |
| GET | `/qrcode/poll` | 轮询扫码状态 |
| GET | `/status` | 获取绑定状态 |
| DELETE | `/unbind` | 解绑账号 |
| GET | `/folders` | 获取收藏夹列表 |
| GET | `/folders/{type}/{id}` | 获取收藏夹详情 |

---

## GET /qrcode

生成 B站登录二维码。

### 响应

```json
{
  "url": "https://passport.bilibili.com/h5/login/scan?...",
  "qrcode_key": "abc123..."
}
```

### 前端使用

```typescript
// 1. 获取二维码
const { url, qrcode_key } = await bilibiliApi.getQRCode();

// 2. 生成二维码图片（使用 qrcode 库）
QRCode.toCanvas(canvasElement, url);

// 3. 开始轮询
pollQRCodeStatus(qrcode_key);
```

---

## GET /qrcode/poll

轮询二维码扫描状态。

### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| qrcode_key | string | ✅ | 二维码 key |

### 响应

```json
{
  "status": "confirmed",
  "message": "登录成功"
}
```

### 状态值

| status | 说明 | 操作 |
|--------|------|------|
| `waiting` | 等待扫码 | 继续轮询 |
| `scanned` | 已扫码待确认 | 继续轮询 |
| `confirmed` | 登录成功 | 停止轮询，刷新状态 |
| `expired` | 二维码过期 | 重新生成 |
| `error` | 错误 | 显示错误信息 |

### 前端轮询示例

```typescript
async function pollQRCodeStatus(qrcodeKey: string) {
  const interval = setInterval(async () => {
    const { status, message } = await bilibiliApi.pollQRCode(qrcodeKey);
    
    if (status === 'confirmed') {
      clearInterval(interval);
      showSuccess('绑定成功！');
      refreshBindStatus();
    } else if (status === 'expired') {
      clearInterval(interval);
      showError('二维码已过期，请重新生成');
    }
  }, 2000); // 每 2 秒轮询一次
}
```

---

## GET /status

获取 B站账号绑定状态。

### 响应

```json
{
  "is_bound": true,
  "bilibili_uid": "12345678",
  "username": "用户昵称",
  "is_vip": true,
  "is_expired": false
}
```

---

## DELETE /unbind

解绑 B站账号。

### 响应

```json
{
  "message": "解绑成功"
}
```

---

## GET /folders

获取用户 B站账号的收藏夹列表。

### 响应

```json
{
  "created": [
    {
      "id": "123456",
      "title": "我的收藏",
      "media_count": 42,
      "folder_type": "favlist"
    }
  ],
  "collected_folders": [
    {
      "id": "789012",
      "title": "订阅的收藏夹",
      "media_count": 100,
      "folder_type": "favlist"
    }
  ],
  "collected_seasons": [
    {
      "id": "345678",
      "title": "订阅的合集",
      "media_count": 20,
      "folder_type": "season"
    }
  ]
}
```

### 收藏夹类型

| folder_type | 说明 |
|-------------|------|
| `favlist` | 普通收藏夹 |
| `season` | 合集/系列 |

---

## GET /folders/{type}/{id}

获取收藏夹/合集的视频列表。

### 路径参数

| 参数 | 说明 |
|------|------|
| type | `favlist` 或 `season` |
| id | 收藏夹/合集 ID |

### 响应

```json
{
  "id": "123456",
  "title": "我的收藏",
  "media_count": 42,
  "folder_type": "favlist",
  "videos": [
    {
      "bvid": "BV1xx411c7mD",
      "title": "视频标题",
      "author": "UP主",
      "duration": 754,
      "cover_url": "https://...",
      "view_count": 10000
    }
  ]
}
```

---

## 完整绑定流程

```
1. GET /qrcode          获取二维码
         ↓
2. 用户扫码              使用 B站 App 扫描
         ↓
3. GET /qrcode/poll     轮询状态（每 2 秒）
         ↓
4. status=confirmed     绑定成功
         ↓
5. GET /status          确认绑定状态
         ↓
6. GET /folders         获取收藏夹列表
         ↓
7. GET /folders/{t}/{i} 查看收藏夹内容
         ↓
8. POST /videos         导入视频到 AliceLM
```
