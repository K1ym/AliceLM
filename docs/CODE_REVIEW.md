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
