# AliceLM 部署指南

## 架构概览

```
                    ┌─────────────┐
                    │   Nginx     │ (可选反向代理)
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │   Web:3000  │ │  API:8000   │ │   Worker    │
    │  (Next.js)  │ │  (FastAPI)  │ │  (后台任务)  │
    └─────────────┘ └──────┬──────┘ └──────┬──────┘
                           │               │
                    ┌──────▼───────────────▼──────┐
                    │         Redis:6379          │
                    └─────────────────────────────┘
```

## 快速开始

### 1. 准备服务器

```bash
# 安装 Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 安装 Docker Compose
sudo apt install docker-compose-plugin
```

### 2. 克隆项目

```bash
git clone https://github.com/YOUR_USERNAME/AliceLM.git
cd AliceLM
```

### 3. 配置环境变量

```bash
cp .env.example .env
nano .env
```

必须配置的变量：
```env
# LLM API (必须)
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.openai.com/v1

# JWT 密钥 (生产必须修改)
JWT_SECRET=your-super-secret-key-change-in-production

# B站 Cookie (可选，用于获取收藏夹)
BILIBILI_COOKIE=your_cookie
```

### 4. 启动服务

```bash
# 生产环境
docker compose -f docker-compose.prod.yml up -d

# 查看日志
docker compose -f docker-compose.prod.yml logs -f
```

### 5. 访问应用

- 前端: http://your-server:3000
- API: http://your-server:8000
- API 文档: http://your-server:8000/docs

---

## CI/CD 配置

### GitHub Secrets

在 GitHub 仓库设置中添加以下 Secrets:

| Secret | 说明 | 示例 |
|--------|------|------|
| `SERVER_HOST` | 服务器 IP | `123.456.789.0` |
| `SERVER_USER` | SSH 用户名 | `ubuntu` |
| `SERVER_SSH_KEY` | SSH 私钥 | `-----BEGIN...` |
| `DEPLOY_PATH` | 部署目录 | `/opt/alicelm` |
| `API_URL` | API 地址 | `http://api:8000` |

### 工作流程

1. **推送代码** -> main 分支
2. **自动构建** -> 前端 + 后端测试
3. **构建镜像** -> 推送到 GitHub Container Registry
4. **自动部署** -> SSH 到服务器拉取并重启

---

## Nginx 反向代理 (推荐)

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # 前端
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # SSE 流式响应支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
    }
}
```

---

## 常用命令

```bash
# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 查看日志
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f api
docker compose -f docker-compose.prod.yml logs -f worker

# 重启服务
docker compose -f docker-compose.prod.yml restart

# 更新部署
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --force-recreate

# 清理
docker system prune -af
```

---

## 数据备份

```bash
# 备份数据库
cp data/bili_learner.db data/bili_learner.db.backup

# 备份配置
tar -czvf config-backup.tar.gz config/ .env
```

---

## 故障排查

### 服务无法启动
```bash
# 检查端口占用
sudo lsof -i :3000
sudo lsof -i :8000

# 检查 Docker 日志
docker compose -f docker-compose.prod.yml logs --tail=100
```

### API 连接失败
```bash
# 检查网络
docker network ls
docker network inspect alicelm_default
```

### 内存不足
```bash
# 检查资源使用
docker stats
```
