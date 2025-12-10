# Alice 升级路线图：从 RAG Chat 到 Agentic AI

## 核心结论

从代码现状看，Alice 的"Agent 底座"已经长得很像 Claude Code / Gemini CLI / Manus，但现在更多被当成一个 RAG Chat + 视频流水线在用。真正缺的是：

1. **更强的 Agent Loop 抽象与自我校正**
2. **和它匹配的 Agentic UI**
3. **围绕 Timeline/Knowledge/UserConfig 打造"如何理解你 → 如何陪你进化"的认知框架**

## 开发原则

- **先后端，后前端**
- **借假修真**：在开发新特性时，强制修复关联的技术债

---

## Phase 1：基础加固与技术债清理（第 1-2 周）

### 目标

聚焦地基与安全，为后续三条线打好基础。

### 新特性

无（本阶段专注技术债清理）

### 必修技术债

| 技术债 | 位置 | 关联性 | 优先级 |
|--------|------|--------|--------|
| tenant_id=1 硬编码 | `alice/agent/tools/basic.py:165` | 阻塞 Agent Loop 多租户语义 | P0 |
| user_id=None | `apps/api/routers/agent.py:91` | 阻塞 AgentRun 语义与审计 | P0 |
| CI 测试失败不阻断 | `.github/workflows/deploy.yml` | 保障后续交付质量 | P0 |
| Debug 认证旁路 | `apps/api/deps.py` | 安全风险 | P0 |
| RBAC 缺失 | `apps/api/routers/console.py` | 安全风险 | P0 |
| API Key 明文存储 | `apps/api/routers/config.py` | 安全风险 | P0 |
| is_active 未校验 | `apps/api/deps.py`, `auth.py` | 安全风险 | P0 |

### 涉及文件

```
alice/agent/tools/basic.py
apps/api/routers/agent.py
apps/api/deps.py
apps/api/routers/auth.py
apps/api/routers/console.py
apps/api/routers/config.py
.github/workflows/deploy.yml
```

### API 变更

- 无对外接口变更
- 补充认证中间件

### 数据库变更

- 无（若 API Key 加密需检查列长度/格式兼容）

### 风险与应对

| 风险 | 应对 |
|------|------|
| RBAC 覆盖不全 | 增量审计 + 强制中间件 |
| CI 阻断影响节奏 | 提前梳理最小必跑用例 |

---

## Phase 2：Agent Loop 升级 + Agentic UI 基线（第 3-4 周）

### 目标

增强 Agent 语义，完成上下文组装，为 Agentic UI 提供后端支持。

### 新特性

1. **AgentRun/AgentStep 语义扩展**
   - 新增字段：`plan_json`, `step_kind`, `safety_level`, `requires_user_confirm`

2. **ContextAssembler 完善**
   - 接入 RAG（ChromaDB/RAGFlow）
   - 接入 Knowledge Graph
   - 接入 TimelineService

3. **Agent 主循环升级**
   - 显式 Plan 阶段
   - SelfCorrector 自我纠正
   - 高风险步骤确认机制

4. **AgentRunPanel 后端 API**
   - 查询 run/step
   - 流式/分页支持
   - 状态过滤

### 必修技术债

| 技术债 | 位置 | 关联性 |
|--------|------|--------|
| RAG 未接入 | `alice/one/context.py:172` | 直接相关 |
| 图谱未接入 | `alice/one/context.py:182` | 直接相关 |
| Timeline 未接入 | `alice/one/context.py:192` | 直接相关 |

### 涉及文件

```
# 模型/Schema
packages/db/models.py          # AgentRun/AgentStep 扩展
apps/api/schemas/agent.py

# 主循环
alice/agent/core.py            # Agent Loop
alice/agent/task_planner.py    # Plan 阶段
alice/agent/self_corrector.py  # 新增：自我纠正

# 上下文
alice/one/context.py           # ContextAssembler

# 服务接入
alice/rag/service.py
services/knowledge/graph.py
alice/one/timeline.py

# API
apps/api/routers/agent.py
apps/api/routers/console.py
```

### API 变更

```python
# AgentRun DTO 扩展
class AgentRunDetail(BaseModel):
    id: int
    tenant_id: int
    user_id: int | None
    scene: str
    query: str
    status: str
    plan_json: str | None        # 新增
    safety_level: str            # 新增：low/normal/high
    answer: str | None
    citations: str | None
    steps: list[AgentStepDetail]
    created_at: datetime
    completed_at: datetime | None

# AgentStep DTO 扩展
class AgentStepDetail(BaseModel):
    id: int
    step_idx: int
    kind: str                    # 新增：plan/tool/observe/reflect/await_confirm
    thought: str | None
    tool_name: str | None
    tool_args: str | None
    observation: str | None
    error: str | None
    requires_user_confirm: bool  # 新增
    created_at: datetime
```

### 数据库变更

```sql
-- AgentRun 表
ALTER TABLE agent_runs ADD COLUMN plan_json TEXT;
ALTER TABLE agent_runs ADD COLUMN safety_level VARCHAR(20) DEFAULT 'normal';

-- AgentStep 表
ALTER TABLE agent_steps ADD COLUMN kind VARCHAR(20) DEFAULT 'tool';
ALTER TABLE agent_steps ADD COLUMN requires_user_confirm BOOLEAN DEFAULT FALSE;
```

### 风险与应对

| 风险 | 应对 |
|------|------|
| 历史数据迁移 | 列默认值 + 逐步回填 |
| SelfCorrector 增加时延 | 超时与短路策略 |
| 确认流程卡死 | 超时/重试机制 |

---

## Phase 3：Agentic UI 完备 + 高风险确认 + 记忆/任务中心（第 5-6 周）

### 目标

完善 Agentic UI 后端支持，实现人机协作控制。

### 新特性

1. **高风险步骤确认 API**
   - POST `/agent/runs/{run_id}/steps/{step_id}/confirm`
   - 幂等处理

2. **任务中心 API**
   - 任务列表/状态/重试/取消

3. **记忆中心 API**
   - 检索/写入/标签/来源记录

### 必修技术债

| 技术债 | 位置 | 关联性 |
|--------|------|--------|
| 正文抓取未实现 | `alice/search/search_agent.py:215` | 任务中心/搜索类任务可用性 |
| video_ids 过滤未实现 | `alice/rag/service.py:163` | 记忆中心质量 |

### 涉及文件

```
# API
apps/api/routers/agent.py      # confirm endpoint
apps/api/routers/tasks.py      # 新增：任务中心
apps/api/routers/memory.py     # 新增：记忆中心

# 搜索
alice/search/search_agent.py

# RAG
alice/rag/service.py

# 模型
packages/db/models.py          # 确认记录
```

### API 变更

```python
# 确认 API
@router.post("/runs/{run_id}/steps/{step_id}/confirm")
async def confirm_step(
    run_id: int,
    step_id: int,
    body: ConfirmStepRequest,  # { approved: bool, modified_args?: str }
    user: User = Depends(get_current_user)
) -> ConfirmStepResponse

# 任务中心 API
@router.get("/tasks")
async def list_tasks(
    status: str | None = None,
    page: int = 1,
    limit: int = 20
) -> TaskListResponse

@router.post("/tasks/{task_id}/retry")
async def retry_task(task_id: int) -> TaskResponse

@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: int) -> TaskResponse

# 记忆中心 API
@router.get("/memory/insights")
async def list_insights(
    tags: list[str] | None = None,
    video_id: int | None = None
) -> InsightListResponse

@router.post("/memory/insights")
async def create_insight(body: CreateInsightRequest) -> InsightResponse

@router.delete("/memory/insights/{insight_id}")
async def delete_insight(insight_id: int) -> None
```

### 数据库变更

```sql
-- 步骤确认记录
ALTER TABLE agent_steps ADD COLUMN confirmed_at TIMESTAMP;
ALTER TABLE agent_steps ADD COLUMN confirmed_by INTEGER REFERENCES users(id);
ALTER TABLE agent_steps ADD COLUMN confirm_result VARCHAR(20);  -- approved/declined

-- 记忆/洞察表（如需新建）
CREATE TABLE user_insights (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    content TEXT NOT NULL,
    tags TEXT,  -- JSON array
    source_type VARCHAR(20),  -- video/conversation/agent_run
    source_id INTEGER,
    pinned BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX ix_user_insights_user (user_id),
    INDEX ix_user_insights_tenant_pinned (tenant_id, pinned)
);
```

### 风险与应对

| 风险 | 应对 |
|------|------|
| 并发确认幂等性 | 乐观锁/去重 token |
| 外部抓取不稳定 | 重试与降级缓存 |

---

## Phase 4：认知进化框架落地（第 7-8 周）

### 目标

实现 UserModelService，让 Alice 从"工具"进化为"伴侣"。

### 新特性

1. **UserModelService**
   - 从 TimelineEvent/LearningRecord/Message 蒸馏用户模型
   - 概念掌握度、风格偏好、关注主题

2. **ContextAssembler 个性化**
   - 使用 UserModel 生成个性化 system prompt

3. **记忆中心完善**
   - 画像写入
   - 偏好回流至 RAG/Graph

### 涉及文件

```
# 用户模型
alice/user_model/service.py    # 新增
alice/user_model/schemas.py    # 新增

# Timeline/Learning
alice/one/timeline.py
services/knowledge/learning.py

# Context
alice/one/context.py

# 记忆中心
apps/api/routers/memory.py
```

### 核心数据结构

```python
@dataclass
class UserConceptState:
    level: Literal["unknown", "learning", "familiar", "mastered"]
    last_seen_at: datetime
    examples: list[int]  # video_ids

@dataclass
class UserModel:
    # 概念掌握度
    concept_states: dict[str, UserConceptState]
    # 交互偏好
    style: dict[str, Any]  # tone, language_ratio, preferred_length
    # 关注主题
    favorite_tags: list[str]
    # 显式 pin 的长期记忆
    pinned_insights: list[dict]
```

### API 变更

```python
# 用户画像 API（调试用）
@router.get("/me/profile")
async def get_user_profile(
    user: User = Depends(get_current_user)
) -> UserProfileResponse

# 偏好更新
@router.patch("/me/preferences")
async def update_preferences(
    body: UpdatePreferencesRequest,
    user: User = Depends(get_current_user)
) -> UserProfileResponse
```

### 数据库变更

```sql
-- 用户画像存储（复用 user_configs）
-- key = "user_model", value = JSON

-- 或新建专用表
CREATE TABLE user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
    concept_states JSONB DEFAULT '{}',
    style JSONB DEFAULT '{}',
    favorite_tags JSONB DEFAULT '[]',
    updated_at TIMESTAMP DEFAULT NOW(),
    INDEX ix_user_profiles_user (user_id)
);
```

### 风险与应对

| 风险 | 应对 |
|------|------|
| 用户画像隐私与合规 | 敏感字段脱敏，用户可删除 |
| 画像回填性能 | 分批任务 + 索引优化 |
| 个性化 prompt 漂移 | A/B 测试保护 |

---

## 依赖关系图

```
Phase 1 (基础加固)
    │
    ▼
Phase 2 (Agent Loop + UI 基线)
    │
    ▼
Phase 3 (Agentic UI 完备)
    │
    ▼
Phase 4 (认知进化框架)
```

- **Phase 1 → Phase 2**：认证/RBAC/CI 修复后再扩展 AgentRun/Step
- **Phase 2 → Phase 3**：AgentRun/Step 语义完善后，才能暴露 confirm API
- **Phase 3 → Phase 4**：任务/记忆基础到位后，再构建 UserModel

---

## 交付物清单

### Phase 1 交付物
- [ ] tenant_id 从上下文获取
- [ ] user_id 从认证获取
- [ ] CI 测试失败阻断
- [ ] Debug 旁路移除
- [ ] RBAC 基线实现
- [ ] API Key 加密存储
- [ ] is_active 校验

### Phase 2 交付物
- [ ] AgentRun/AgentStep 模型扩展
- [ ] ContextAssembler 接入 RAG/Graph/Timeline
- [ ] SelfCorrector 实现
- [ ] AgentRunPanel API

### Phase 3 交付物
- [ ] 步骤确认 API
- [ ] 任务中心 API
- [ ] 记忆中心 API
- [ ] 搜索正文抓取
- [ ] RAG video_ids 过滤

### Phase 4 交付物
- [ ] UserModelService
- [ ] 个性化 ContextAssembler
- [ ] 用户画像 API
- [ ] 记忆中心完善

---

## 下一步行动

**立即开始 Phase 1**：

1. 修复 `alice/agent/tools/basic.py:165` - tenant_id 硬编码
2. 修复 `apps/api/routers/agent.py:91` - user_id=None
3. 修复 CI 配置 - 移除 `|| true`
4. 实现 RBAC 基线
