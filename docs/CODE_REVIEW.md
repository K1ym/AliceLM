# 代码安全审查

## 高优先级问题

### 1. 默认密钥弱且易被滥用
- `packages/config/settings.py` 中的 `secret_key` 默认值为 `"change-me-in-production"`，即使在生产环境未覆盖也会被用于 JWT 签名。【F:packages/config/settings.py†L71-L88】
- 任何获取该默认值的环境都可伪造有效 Token，导致完全未授权访问。
- 建议：强制从环境变量提供随机足够长度的密钥；在启动时校验默认值并拒绝启动。

### 2. 调试模式可绕过认证
- `apps/api/deps.py` 允许在 `config.debug` 为 `True` 且无凭据时直接返回邮箱为 `admin@local` 的用户，实现无 Token 登录。【F:apps/api/deps.py†L36-L88】
- 如果调试模式在生产环境误开启或默认值未被覆盖，将导致任意请求自动获得最高权限用户。
- 建议：删除该后门或仅在明确的开发环境下通过特定标记/白名单开启，并确保生产配置强制关闭。

### 3. 登出未吊销 Token
- `/api/v1/auth/logout` 仅返回消息，未记录或吊销现有 Token；JWT 在到期前始终有效。【F:apps/api/routers/auth.py†L44-L130】
- 账户被盗或密码修改后，旧 Token 仍可继续访问，无法满足安全注销或主动失效要求。
- 建议：引入 Token 黑名单/版本号（如 `token_version` 字段）并在验证时检查，或将有效期缩短并结合刷新令牌流程。

### 4. 全局 B 站 SESSDATA 兜底导致凭证泄露
- `FolderService._resolve_sessdata` 在用户未绑定 B 站账号时回退到全局配置 `config.bilibili.sessdata`，所有租户/用户的收藏夹扫描都会复用该 Cookie。【F:apps/api/services/folder_service.py†L42-L70】
- 任何普通用户都能间接使用该共享凭证访问配置者的 B 站收藏夹，等同于把主账号的会话暴露给全体用户。
- 建议：移除全局 SESSDATA 兜底，强制用户绑定自己的会话；如需运维账号，应按租户隔离且限制可见范围，并对凭证做最小化权限和轮换。

### 5. 停用账号仍可登录和访问
- 登录与鉴权流程未检查 `user.is_active`，`AuthService.authenticate` 和 `get_current_user` 对被停用账户仍返回成功结果。【F:apps/api/services/auth_service.py†L50-L68】【F:apps/api/deps.py†L36-L88】
- 被封禁或停用的用户依旧可以凭旧密码或 Token 继续访问接口，管理员无法即时阻断访问。
- 建议：在登录前、刷新 Token 和每次取当前用户时检查 `is_active`，对不活跃账号返回 403/401 并记录审计日志。

### 6. Docker Compose 指向不存在的 Worker 入口
- `docker-compose.yml` 的 `worker` 服务命令为 `python -m services.worker`，但仓库中不存在 `services/worker.py` 或同名模块，容器启动会立即因模块缺失而退出，后台任务（下载、转写、清理）无法运行。【F:docker-compose.yml†L23-L38】【94b30c†L1-L2】
- 建议：补充实际的 worker 入口（如 Celery/自定义队列消费进程），或调整 Compose 命令到现有调度器/管道启动脚本，并在 CI 中添加存在性/启动校验。

### 7. 多租户数据共用全局下载目录，文件名仅用 BV 号
- 视频下载与处理管道默认目录为 `data/videos`、`data/audio`、`data/transcripts`，子目录只按 `bvid` 或 `source_id` 命名，没有按租户隔离，同一 BV 号在不同租户间会覆盖或复用同一份音视频和转写结果。【F:services/processor/pipeline.py†L29-L42】【F:services/processor/downloader.py†L29-L52】
- 共享目录导致租户间数据污染（缓存/转写被复用或删除）、以及通过路径推断他人处理过的内容，属于结构性越权风险。
- 建议：目录结构加上 `tenant_id/slug` 前缀并在数据库中记录完整路径；旧文件迁移或重新生成，避免跨租户共享。
