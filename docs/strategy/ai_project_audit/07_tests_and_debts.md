# 测试、质量与技术债

## 自动化测试情况

### 测试框架

| 项目 | 配置 |
|------|------|
| 框架 | pytest |
| 异步模式 | `asyncio_mode=strict` |
| 测试目录 | `tests/` |
| 覆盖率工具 | pytest-cov（已安装但未使用） |

### 测试目录结构

```
tests/
├── api/                         # API 路由测试
│   ├── test_agent_api.py
│   ├── test_auth_api.py
│   ├── test_console_api.py
│   ├── test_videos_api.py
│   └── TEST_COVERAGE_REPORT.md
├── integration/                 # 集成测试（仅 __init__.py，空置）
├── unit/                        # 单元测试
│   ├── test_errors.py
│   ├── test_llm.py
│   ├── test_retry.py
│   └── test_summarizer.py
├── test_alice_agent.py          # Agent 结构/契约测试
├── test_alice_one.py            # One 模块结构测试
├── test_architecture_validation.py  # 架构验证
├── test_control_plane.py        # 控制平面配置解析测试
├── test_control_plane_api.py    # 控制平面路由测试
├── test_phase0.py               # 基础设施/DB/配置测试
└── conftest.py                  # 测试配置
```

### 测试覆盖情况

| 模块 | 覆盖状态 | 说明 |
|------|----------|------|
| `alice/errors` | ✅ 有测试 | 单元测试 |
| `packages/retry` | ✅ 有测试 | 单元测试 |
| `services/ai/llm` | ✅ 有测试 | 单元测试 |
| `services/ai/summarizer` | ✅ 有测试 | 单元测试 |
| `alice/control_plane` | ✅ 主要路径 | `test_control_plane.py` 覆盖 YAML 加载 |
| `alice/agent/*` | ⚠️ 结构为主 | 导入/契约检查为主 |
| `apps/api/routers/control_plane` | ⚠️ 部分 | happy path 为主，缺少异常/认证 |
| `apps/api/routers/auth` | ⚠️ 部分 | 4xx/401 防御性用例 |
| `apps/api/routers/agent` | ⚠️ 部分 | 4xx 防御 + 少量 200/401 |
| `apps/api/routers/console` | ⚠️ 部分 | 防御性测试 |
| `apps/api/routers/videos` | ⚠️ 部分 | 4xx/500 测试 |
| `packages/db/*` | ⚠️ 基础 | `test_phase0.py` 覆盖模型 CRUD/租户隔离 |
| `packages/config/*` | ⚠️ 基础 | `test_phase0.py` 验证配置加载 |
| `apps/api/services/*` | ❌ 无测试 | 服务层完全缺失 |
| `services/ai/*` (其他) | ❌ 无测试 | 仅 llm/summarizer 有单测 |
| `services/asr/*` | ⚠️ 仅存在性 | 只做导入验证 |
| `services/downloader/*` | ⚠️ 仅存在性 | 只做存在性检查 |
| `services/knowledge/*` | ❌ 无测试 | 知识服务 |
| `apps/web/*` | ❌ 无测试 | 前端完全无测试 |

### 测试质量问题

- 部分用例为**结构/契约性导入测试**（如 `test_alice_agent.py`），但 `test_phase0.py` 和 `test_control_plane*.py` 已覆盖真实逻辑
- API 测试主要检查 4xx/500 防御性行为，**缺少成功路径测试**
- `tests/integration/` 空置，**路由与服务间整合未验证**
- `TEST_COVERAGE_REPORT.md` 列出大量未覆盖路由，但未见修复（时间停留在 2024-12-04）

## CI / 质量检查

### GitHub Actions 配置

| 文件 | 触发条件 | 内容 |
|------|----------|------|
| `.github/workflows/deploy.yml` | PR / main push | 后端测试 + 前端构建 |
| `.github/workflows/auto-codex-review.yml` | PR | 自动 review 评论 |

### CI 流水线问题

```yaml
# deploy.yml 后端 job
python -m pytest tests/ -v --ignore=tests/integration || true
# ⚠️ 问题：
# 1. || true 导致测试失败不阻断
# 2. 忽略 integration 测试
# 3. 无覆盖率上传
# 4. 无 ruff/mypy/安全扫描
```

```yaml
# deploy.yml 前端 job
npm run build
# ⚠️ 问题：
# 1. 未运行 npm run lint
# 2. 无前端测试
```

### 静态检查工具

| 工具 | 配置状态 | CI 执行 |
|------|----------|---------|
| ruff | ✅ `pyproject.toml` 配置 (E/F/I/N/W) | ❌ 未执行 |
| mypy | ✅ `pyproject.toml` 配置 | ❌ 未执行 |
| pytest-cov | ✅ 已安装 | ❌ 未使用 |
| ESLint (前端) | ⚠️ 脚本存在，无配置文件 | ❌ 未执行 |

## TODO / 技术债清单

### 功能缺失

| 文件 | 行号 | 注释原文 | 理解 |
|------|------|----------|------|
| `alice/search/search_agent.py` | 215 | `# TODO: 实现正文抓取` | 搜索结果正文抓取未实现，影响答案质量 |
| `alice/one/context.py` | 172 | `# TODO: 集成 RAGFlow / Chroma` | 上下文组装缺少向量检索 |
| `alice/one/context.py` | 182 | `# TODO: 集成图谱查询` | 知识图谱未接入 |
| `alice/one/context.py` | 192 | `# TODO: 集成 TimelineService` | 时间线记忆未串联 |
| `services/knowledge/learning.py` | 199 | `# TODO: 基于概念推荐相关视频` | 学习推荐未实现 |

### 安全/隔离问题

| 文件 | 行号 | 注释原文 | 理解 |
|------|------|----------|------|
| `alice/agent/tools/basic.py` | 165 | `tenant_id=1,  # TODO: 从上下文获取` | 工具层租户硬编码，存在越权风险 |
| `apps/api/routers/agent.py` | 91 | `user_id=None,  # TODO: 从认证中获取` | Agent API 未绑定真实用户，审计缺失 |

### 数据处理问题

| 文件 | 行号 | 注释原文 | 理解 |
|------|------|----------|------|
| `services/downloader/bbdown.py` | 360 | `# TODO: 直接调用B站API检查字幕可用性` | 字幕可用性未验证，下载鲁棒性不足 |
| `alice/rag/service.py` | 163 | `# TODO: 如果指定了video_ids，需要过滤` | RAG 召回未按指定视频过滤，易返回无关内容 |

## 技术债优先级建议

### P0 - 立即修复（阻塞上线）

| # | 问题 | 位置 | 影响 | 建议 |
|---|------|------|------|------|
| 1 | CI 测试失败不阻断 | `.github/workflows/deploy.yml` | 质量门禁失效 | 移除 `\|\| true` |
| 2 | 租户隔离硬编码 | `alice/agent/tools/basic.py:165` | 越权访问风险 | 从上下文获取 tenant_id |
| 3 | Agent API 无用户绑定 | `apps/api/routers/agent.py:91` | 审计/权限缺失 | 从认证获取 user_id |
| 4 | 核心路由无正向测试 | `/agent/chat`, `/console/*`, `/videos/*` | 回归风险高 | 补充 TestClient 测试 |

### P1 - 短期改进（1-2 周）

| # | 问题 | 位置 | 影响 | 建议 |
|---|------|------|------|------|
| 5 | RAG/图谱/Timeline 未接入 | `alice/one/context.py` | 上下文质量差 | 完成集成 |
| 6 | 搜索正文抓取未实现 | `alice/search/search_agent.py` | 答案质量差 | 实现正文抓取 |
| 7 | video_ids 过滤未实现 | `alice/rag/service.py` | 返回无关内容 | 添加过滤逻辑 |
| 8 | 服务层无测试 | `services/*` | 外部依赖不可控 | 添加 mock 测试 |
| 9 | 前端无测试/lint | `apps/web/` | 前端质量不可控 | 添加基础测试，CI 运行 lint |

### P2 - 中期改进（1 个月）

| # | 问题 | 位置 | 影响 | 建议 |
|---|------|------|------|------|
| 10 | 字幕可用性未检查 | `services/downloader/bbdown.py` | 下载失败率高 | 调用 API 预检 |
| 11 | 概念推荐未实现 | `services/knowledge/learning.py` | 学习体验差 | 实现推荐逻辑 |
| 12 | 无覆盖率收集 | CI | 质量不可见 | 启用 pytest-cov |
| 13 | ruff/mypy 未在 CI 执行 | CI | 代码质量不可控 | 添加到 CI |
| 14 | 集成测试空置 | `tests/integration/` | 端到端未验证 | 补充集成测试 |

## 改进建议

### CI 修复示例

```yaml
# .github/workflows/deploy.yml
backend:
  steps:
    - name: Lint
      run: |
        pip install ruff mypy
        ruff check .
        mypy packages/ apps/ alice/ services/

    - name: Test
      run: |
        python -m pytest tests/ -v --cov=. --cov-report=xml
        # 移除 || true，让测试失败阻断

    - name: Upload coverage
      uses: codecov/codecov-action@v3

frontend:
  steps:
    - name: Lint
      run: npm run lint

    - name: Build
      run: npm run build
```

### 测试补充优先级

1. **认证流程** - 登录成功/失败、Token 校验
2. **Agent 对话** - 正常对话、流式响应、错误处理
3. **视频处理** - 导入、处理、查询
4. **配置管理** - 读取、更新、验证
