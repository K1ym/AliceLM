# 后端测试覆盖 & 风险报告

> 生成时间: 2024-12-04
> 测试框架: pytest + FastAPI TestClient

---

## 1. 测试运行摘要

### 1.1 现有测试

| 文件 | 测试数 | 状态 |
|------|--------|------|
| `tests/test_alice_agent.py` | 77 | ✅ 全部通过 |
| `tests/test_alice_one.py` | 10 | ✅ 全部通过 |
| `tests/test_phase0.py` | 10 | ⚠️ 2 个失败 |

### 1.2 新增 API 集成测试

| 文件 | 测试数 | 设计目标 |
|------|--------|---------|
| `tests/api/test_auth_api.py` | 23 | Auth 认证安全 |
| `tests/api/test_agent_api.py` | 15 | Agent Chat API |
| `tests/api/test_console_api.py` | 27 | Console 监控 API |
| `tests/api/test_videos_api.py` | 20 | 视频 CRUD API |

---

## 2. 发现的问题

### 2.1 🔴 严重问题

#### BUG-001: Console Router 未注册

**位置**: `apps/api/main.py`

**问题**: `console.py` 路由文件存在但未在 main.py 中注册

**状态**: ✅ 已修复

```python
# 已添加
from .routers import ... console
app.include_router(console.router, prefix="/api/v1/console", tags=["Console"])
```

#### BUG-002: 测试数据库隔离问题

**问题**: TestClient 使用的数据库会话与 API 内部使用的不一致，导致 `no such table` 错误

**影响**: 大量 API 集成测试无法运行

**根因**: 
- `test_app` fixture 创建了内存数据库
- 但 API 内部的依赖注入可能使用不同的数据库连接

**建议修复**:
1. 使用文件型 SQLite 替代内存 SQLite
2. 确保 `get_db` 依赖正确被覆盖
3. 考虑使用 pytest-asyncio 处理异步问题

### 2.2 🟡 中等问题

#### RISK-001: API 输入验证不完善

测试用例设计发现以下边界情况可能未被正确处理：

- **空字符串 query**: 应返回 422，实际行为未知
- **超长输入**: 10000+ 字符的 query 可能导致问题
- **特殊字符**: SQL 注入、路径遍历等攻击向量

#### RISK-002: 错误响应格式不一致

部分 API 的错误响应可能不包含标准的 `detail` 字段

### 2.3 🟢 低风险

#### INFO-001: Pydantic V2 废弃警告

多个 schema 类使用了 Pydantic V1 风格的 `class Config`，应迁移到 `model_config = ConfigDict(...)`

**文件**:
- `apps/api/schemas.py`
- `apps/api/routers/conversations.py`
- `packages/config/settings.py`

---

## 3. 路由覆盖情况

### 3.1 已有测试覆盖

| 路由 | 端点 | 测试状态 |
|------|------|---------|
| `/api/v1/agent` | GET /strategies | ✅ 通过 |
| `/api/v1/agent` | GET /scenes | ✅ 通过 |
| `/api/v1/auth` | POST /login (422) | ✅ 通过 |
| `/api/v1/auth` | POST /register (422) | ✅ 通过 |
| `/api/v1/auth` | GET /me (401) | ✅ 通过 |

### 3.2 需要修复测试环境后验证

| 路由 | 端点 | 预期测试 |
|------|------|---------|
| `/api/v1/agent` | POST /chat | 认证、输入验证、场景处理 |
| `/api/v1/console` | 全部 | 认证、日志查询、Eval 执行 |
| `/api/v1/videos` | 全部 | CRUD、队列、转写 |
| `/api/v1/conversations` | 全部 | 对话管理、流式消息 |
| `/api/v1/qa` | 全部 | 知识库问答、搜索 |
| `/api/v1/knowledge` | 全部 | 图谱、学习记录 |
| `/api/v1/bilibili` | 全部 | B站绑定、收藏夹 |
| `/api/v1/config` | 全部 | 配置管理 |

### 3.3 完全无测试的端点

- `/api/v1/folders` - 收藏夹管理
- `/api/v1/system` - 系统管理（存储、清理）
- `/api/v1/suggestions` - 灵感建议

---

## 4. 模块级测试覆盖

### 4.1 已覆盖模块

| 模块 | 测试文件 | 覆盖程度 |
|------|---------|---------|
| `alice/agent/core.py` | test_alice_agent.py | ✅ 完整 |
| `alice/agent/strategy.py` | test_alice_agent.py | ✅ 完整 |
| `alice/agent/tool_router.py` | test_alice_agent.py | ✅ 完整 |
| `alice/agent/tool_executor.py` | test_alice_agent.py | ✅ 完整 |
| `alice/agent/task_planner.py` | test_alice_agent.py | ✅ 完整 |
| `alice/agent/mcp_client.py` | test_alice_agent.py | ✅ 完整 |
| `alice/agent/permissions.py` | test_alice_agent.py | ✅ 完整 |
| `alice/agent/run_logger.py` | test_alice_agent.py | ✅ 基础 |
| `alice/eval/*` | test_alice_agent.py | ✅ 完整 |
| `alice/one/*` | test_alice_one.py | ✅ 完整 |
| `alice/search/*` | test_alice_agent.py | ✅ 完整 |

### 4.2 未覆盖模块

| 模块 | 风险等级 | 建议 |
|------|---------|------|
| `apps/api/services/*` | 🟡 中 | 添加服务层单元测试 |
| `apps/api/routers/*` | 🔴 高 | 修复测试环境后覆盖 |
| `services/ai/*` | 🟡 中 | Mock LLM 调用后测试 |
| `services/asr/*` | 🟢 低 | 需要 Mock 外部服务 |
| `services/downloader/*` | 🟢 低 | 需要 Mock 外部服务 |

---

## 5. 风险点

### 5.1 高风险

1. **API 层无集成测试保护**
   - 任何路由更改都可能破坏前端
   - 建议：修复测试环境，添加 CI 强制要求

2. **外部服务依赖**
   - LLM、ASR、Bilibili API 无 Mock
   - 测试需要真实 API Key 才能通过

### 5.2 中风险

1. **数据库迁移**
   - 无迁移测试
   - 建议：添加 Alembic 迁移验证

2. **并发处理**
   - 无并发测试
   - 建议：使用 locust 或 pytest-asyncio 测试

### 5.3 低风险

1. **Pydantic V2 兼容性**
   - 大量废弃警告
   - 建议：逐步迁移

---

## 6. 建议优先级

### P0 - 阻塞问题

1. 修复 `test_app` fixture 的数据库隔离问题
2. 确保所有 API 测试可以独立运行

### P1 - 上线前必须

1. 为 `/api/v1/agent/chat` 添加完整的功能测试
2. 为 `/api/v1/console/*` 添加功能测试
3. 为核心 CRUD 端点添加 happy path 测试

### P2 - 持续改进

1. 添加 pytest-cov 生成覆盖率报告
2. 配置 CI 强制要求测试通过
3. 添加性能/压力测试

---

## 7. 测试命令

```bash
# 运行所有测试
pytest tests/ -v

# 运行特定模块测试
pytest tests/test_alice_agent.py -v

# 运行 API 测试（需修复环境）
pytest tests/api/ -v

# 生成覆盖率报告
pytest tests/ --cov=alice --cov=apps --cov-report=html
```

---

## 附录：测试文件清单

```
tests/
├── __init__.py
├── conftest.py              # Fixtures
├── test_alice_agent.py      # Agent 核心模块测试
├── test_alice_one.py        # Identity/Timeline 测试
├── test_phase0.py           # 基础结构测试
└── api/
    ├── __init__.py
    ├── test_agent_api.py    # Agent API 集成测试
    ├── test_auth_api.py     # Auth API 集成测试
    ├── test_console_api.py  # Console API 集成测试
    └── test_videos_api.py   # Videos API 集成测试
```
