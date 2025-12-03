# BiLearner API 联调文档

## 概览

后端服务基于 **FastAPI** 构建，提供 RESTful API。

### 服务状态

| 模块 | 状态 | 说明 |
|------|------|------|
| Auth (认证) | ✅ Ready | JWT认证 |
| Videos (视频) | ✅ Ready | CRUD + 转写 |
| Folders (收藏夹) | ✅ Ready | 监控管理 |
| QA (问答) | ✅ Ready | RAG问答 |
| Knowledge (知识图谱) | ✅ Ready | 概念关联 |

### 启动方式

```bash
# 后端 API (端口 8000)
cd bili2text-main
source bili2text-venv/bin/activate
uvicorn apps.api.main:app --reload --port 8000

# 前端 (端口 3000)
cd apps/web
pnpm dev
```

### API 文档

启动后访问:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- 健康检查: http://localhost:8000/health

---

## 认证

所有 `/api/v1/*` 端点需要 JWT Token (除了 `/auth/login`)

### 获取 Token

```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### 使用 Token

```bash
GET /api/v1/videos
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

---

## API 端点详情

详见:
- [Videos API](./VIDEOS.md) - 视频CRUD、转写
- [QA API](./QA.md) - 知识库问答、语义搜索
- [Folders API](./FOLDERS.md) - 收藏夹管理
- [Config](./CONFIG.md) - 配置管理 (ASR/LLM/通知)

## 功能完成度

| 功能 | 后端 | 前端 | 说明 |
|------|------|------|------|
| 视频导入 | ✅ | ✅ | URL导入(SmartInput智能识别) |
| 视频列表 | ✅ | ✅ | 分页、筛选、搜索 |
| 视频详情 | ✅ | ✅ | 摘要、转写、B站嵌入播放 |
| 知识问答 | ✅ | ✅ | RAG问答+来源引用 |
| 收藏夹管理 | ✅ | ✅ | 添加、删除 |
| 配置管理 | ✅ | ✅ | ASR/LLM/通知设置 |
| 模型切换 | ✅ | ✅ | 支持多种LLM提供商 |

详见 [CONFIG.md](./CONFIG.md)

---

## 前端联调配置

### 1. 环境变量

`apps/web/.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 2. API 代理 (Next.js)

`apps/web/next.config.mjs`:
```javascript
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://localhost:8000/api/v1/:path*',
      },
    ];
  },
};
```

### 3. 前端 API 封装

已在 `apps/web/src/lib/api.ts` 中完成封装:

```typescript
import { videosApi, qaApi, foldersApi } from '@/lib/api';

// 获取视频列表
const { data } = await videosApi.list({ page: 1, status: 'done' });

// 提问
const answer = await qaApi.ask('这个视频讲了什么？', [videoId]);

// 添加收藏夹
await foldersApi.add('12345678', 'favlist');
```

---

## 联调步骤

### Step 1: 启动服务

```bash
# Terminal 1 - 后端
uvicorn apps.api.main:app --reload --port 8000

# Terminal 2 - 前端
cd apps/web && pnpm dev
```

### Step 2: 验证连接

```bash
# 检查后端
curl http://localhost:8000/health

# 检查 API
curl http://localhost:8000/api/v1
```

### Step 3: 测试认证

```bash
# 登录获取 token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}'
```

### Step 4: 测试视频接口

```bash
# 获取视频列表
curl http://localhost:8000/api/v1/videos \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 常见问题

### CORS 错误

后端已配置允许 `localhost:3000`，如果仍有问题检查:
- 确保后端在 8000 端口运行
- 确保前端在 3000 端口运行
- 检查请求是否带有正确的 Headers

### 401 Unauthorized

- Token 过期，重新登录
- Token 格式错误，检查 `Bearer ` 前缀
- 未传 Authorization header

### 500 Internal Error

- 检查后端日志
- 确保数据库文件存在 (`data/bili_learner.db`)
- 确保配置文件正确 (`config/default.yaml`)
