# 🚀 AliceLM 路线图（当前）

> 更新日期：2025-12-10  
> 说明：本路线图取代原 1204PLAN 和旧版 ROADMAP。详细拆解见 `docs/strategy/ai_project_audit/08_upgrade_roadmap.md`，调研参考 `docs/research/AGENT_RESEARCH.md`。

---

## 文档基准与范围
- Canonical 路线图：本文件 + `docs/strategy/ai_project_audit/08_upgrade_roadmap.md`。
- 历史方案：`docs/archive/ALICE_VISION_ANALYSIS.md` 保留为愿景解读，内容不再更新；`docs/1204PLAN.md` 已删除。
- 本文聚焦「当前状态 → 缺口 → 里程碑」，避免和产品/PRD/架构文档重复。

---

## 当前状态（事实对齐）
- **Pipeline**：B站导入 → 下载/ASR → 摘要/RAG 已跑通；多租户模型存在（Tenant/User/Video），但部分硬编码/漏注入仍待修复（见 upgrade_roadmap Phase 1）。
- **Agent 层**：`AliceAgentCore` 作为统一入口已接入 `/api/agent/chat`，但运行模式仍是「单轮 LLM + 可选一次工具调用」；`TaskPlanner`/`ToolExecutor`（ReAct 循环）已实现但未接线；Self-corrector/高风险确认未落地。
- **工具体系**：`ToolRouter` 已注册基础/搜索/MCP 工具，控制平面提供工具注册表，但工具作用域与身份/租户注入仍需补完。
- **上下文与人格**：`AliceIdentityService`、`ContextAssembler` 存在，RAG/Graph/Timeline 接口部分是 TODO/占位；UserModel/记忆中心未实现。
- **前端**：Next.js 应用可用，Chat 入口已走 `/api/agent/chat`；部分旧路由占位需清理，缺少 AgentRun/Step 可视化与确认流。
- **安全与质量**：认证绕过/tenant_id 硬编码等 P0 安全债尚未关闭；测试覆盖集中在骨架与 API 烟囱，缺少 Agent 循环与工具执行的回归。

---

## 关键缺口
- **Agent 主循环未启用**：Planner/Executor 未接线，LLM 没有多步 ReAct、无自我纠错/确认/回溯。
- **上下文与记忆严重不足**：
  - RAG/Graph/Timeline 检索全是 TODO 空实现
  - 用字符数代替 token 数（`len(content)` 而非 tiktoken）
  - 硬编码 6 条消息 / 20k 字符限制，无动态窗口管理
  - 无 Entity Memory、Summary Buffer、Knowledge Graph Memory
  - 未利用 Prompt Caching（Claude/GPT-4 支持）
- **安全/多租户**：tenant_id/user_id 注入缺失；认证旁路；工具调用缺乏安全级别与审计。
- **异常处理缺陷**：大量裸 `except Exception` 吞异常，阻断定位与告警，可能掩盖认证/支付/外部依赖失败。
- **多源迁移未完成**：仍以 `bvid` 为核心字段，未统一为 `source_type + source_id`，阻碍多源扩展与数据模型一致性。
- **可观测性与复盘**：AgentRun/Step 结构未扩展，缺少 tool trace、confirm、超时/熔断与回放 UI。
- **人机协同**：缺少「高风险步骤确认」「任务中心」「记忆中心」等 Jarvis 式交互。

---

## 里程碑（Jarvis 目标导向）

### M1：地基与安全（1–2 周）
- 关闭 P0 安全/多租户债（见 upgrade_roadmap Phase 1）：tenant_id 注入、认证旁路、RBAC、API Key 加密、CI 阻断。
- **异常处理规范化（P0）**：
  - 制定异常基类与分级（沿用 `alice.errors`），禁用裸 `except Exception`。
  - 分批整改热点模块（API routers、services、agent、downloader、scheduler、LLM providers），用特定异常并补充 logging/metrics。
  - CI 添加"禁止裸 except Exception"检查（ruff/flake8 规则），关键路径补异常路径测试。
- **多源数据模型迁移（P0）**：
  - 数据层：完成迁移脚本，唯一约束改为 `(tenant_id, source_type, source_id)`，移除残留 bvid 字段/索引。
  - 服务/API：统一参数与返回结构为 `source_type + source_id`，B 站 bvid 留在 provider 层解析。
  - 前端：types/api/组件替换 bvid，保留过渡映射；同步接口 mock。
  - 测试/文档：更新 fixtures/用例，补多源场景测试；API 示例替换字段。
- 扩展 AgentRun/AgentStep schema（plan_json/safety_level/kind/requires_user_confirm），补齐 API DTO。
- 基线观测：记录 tool_trace、LLM 调用摘要、错误码；新增最小回归测试（agent chat happy path + tool error）。

### M2：启用主循环（2–3 周）
- 将 `TaskPlanner` + `ToolExecutor` 接入 `AliceAgentCore.run_task`，支持 ReAct 多步、终止工具、max_steps/超时。
- 接入 ContextAssembler：RAG/Graph/Timeline 三种来源按 scene 注入；工具入参自动补 tenant/user/video。
- Self-corrector：失败/空 observation 时触发一次反思重试；为高风险步骤标记 `requires_user_confirm`。

### M2.5：AliceMem - 自研长上下文记忆系统

> 与 M2/M3 并行推进，为 Agent 主循环提供可靠的长上下文支撑。

**为什么自研（而非 Mem0）**：
- 精确 token 预算（tiktoken），避免用字符数代替 token 数
- 安全级别过滤、Scene/tenant/source_id 粒度检索
- Graph/Timeline/Entity 深度定制，与现有架构无缝集成
- 成本可控、性能可调、安全可审计

**AliceMem 应用场景**：

| 场景 | 应用方式 | 优先级 |
|------|---------|--------|
| **Agent 对话** | 多轮记忆、跨会话检索、用户偏好学习 | P0 |
| **知识管理** | Video/文档摘要、Graph 增量更新、Timeline 事件 | P1 |
| **工具执行** | 调用历史、错误模式学习、上下文感知选择 | P1 |
| **个性化** | 用户画像、学习进度、兴趣推荐 | P2 |
| **跨模块复用** | RAG 增强、搜索缓存、洞察生成 | P2 |
| **未来扩展** | 团队共享、外部系统集成 | P3 |

**核心架构**：
```
┌─────────────────────────────────────────────────────────────┐
│                     Token Budget Manager                     │
│         (tiktoken: system 2k + history 6k + memory 6k)       │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
   [Layer 1]            [Layer 2]            [Layer 3]
   Recent Window        Summary Buffer       Entity Memory
   (原文 N 条)           (压缩摘要)            (KV 实体)
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
         ┌────────────────────┴────────────────────┐
         ▼                                         ▼
   [Layer 4]                               [Layer 5]
   Vector Memory                           Graph/Timeline
   (Chroma 语义检索)                        (结构化知识)
```

**数据流**：
```
User ↔ AgentCore ↔ ContextAssembler ──┐
                                      │ retrieve
                                      ▼
                               [AliceMem]
                              /    |    \
                        recent  summary  vector/entity/graph
                              \    |    /
                               store (messages/tools/content)
Processor/Pipeline ──store_content──────┘
Graph/Timeline ──upsert→ AliceMem
ToolExecutor ──log_tool_run→ AliceMem
```

**模块结构**：
```
services/memory/
├── service.py          # AliceMem Facade: retrieve/store/summarize/forget
├── token_manager.py    # tiktoken 预算分配
├── recent_buffer.py    # Layer 1: 最近窗口
├── summary_buffer.py   # Layer 2: 自动摘要
├── entity_memory.py    # Layer 3: 实体 KV
├── vector_memory.py    # Layer 4: Chroma 检索
├── graph_timeline.py   # Layer 5: 结构化洞察
└── models.py           # DTO/MemoryChunk
```

**核心接口**：
```python
class AliceMem:
    async def retrieve(query, tenant_id, user_id, scene, ...) -> List[MemoryChunk]
    async def store_message(message, role, tenant_id, ...) -> None
    async def store_content(text, tenant_id, source_type, source_id, ...) -> None
    async def summarize_conversation(conversation_id, ...) -> str
    async def log_tool_run(name, args, result, error, ...) -> None
    async def forget(scope, tenant_id, identifier) -> None
```

**集成点**：
- `alice/agent/core.py`: 构建 messages 前调用 `retrieve()`，生成后调用 `store_message()`
- `alice/one/context.py`: 注入 memory 层结果，调用 token_manager 预算
- `services/processor/pipeline.py`: 内容处理后调用 `store_content()`
- `services/knowledge/graph.py`: 写入/读取 graph_timeline
- `alice/agent/tool_executor.py`: 调用 `log_tool_run()` 记录工具执行

**分阶段落地**：

| Phase | 内容 | 验收标准 |
|-------|------|---------|
| **Phase 1** (1周) | tiktoken + Token Budget Manager + Recent Window | 上下文组装遵循 token 预算，无裸字符计数 |
| **Phase 2** (1周) | Summary Buffer + conversation_summaries 表 | 长对话自动摘要，不超预算 |
| **Phase 3** (1-2周) | Entity Memory + Vector Memory (Chroma) | 检索结果含实体+语义片段，元数据过滤生效 |
| **Phase 4** (1周) | Graph/Timeline 集成 + 工具追踪 | 结构化知识可写入/读出，注入对话上下文 |

**数据库新表**（migration: `003_memory.py`）：
- `conversation_summaries` (conversation_id, tenant_id, summary, created_at)
- `entities` (tenant_id, name, type, data JSONB)
- `entity_mentions` (tenant_id, conversation_id, message_id, entity_id)
- `memory_traces` (tenant_id, scene, source_type, source_id, text, vector_ref, metadata JSONB)

**配置项**：
- `MEM_TOKEN_BUDGET_TOTAL`: 总 token 预算（默认 16000）
- `MEM_RECENT_MAX_MESSAGES`: 最近窗口大小（默认 30）
- `MEM_SUMMARY_TRIGGER_TOKENS`: 摘要触发阈值
- `ENABLE_SUMMARY/VECTOR/ENTITY/GRAPH`: 各层启用开关

**风险缓解**：
- 性能：Chroma 预热、分页；缓存 token 计数；摘要频率限流
- 成本：摘要按阈值批处理、低价模型、长度限制
- 回滚：AliceMem 可降级为 recent-only 模式

### M3：人机协同与可视化（2 周）
- API：step 确认 `/agent/runs/{run_id}/steps/{step_id}/confirm`，任务中心 `/tasks` 列表/重试/取消，记忆中心 `/memory/insights` CRUD。
- 前端：AgentRunPanel 展示步骤/工具/日志，支持流式与分页；高风险步骤确认 UI；任务中心/记忆中心 MVP。
- Observability：step trace 持久化，超时/熔断/重试策略落地，基础 metrics（成功率、平均步数）。

### M4：Jarvis 化能力（3–4 周）
- 个性化：UserModelService（概念掌握度/风格/偏好）+ Context 个性化 prompt；记忆中心回流到检索/工具。
- 并行与策略：简单节点图（LangGraph 风格）支持并行工具与条件路由；Research/Timeline 策略可自适应选工具包。
- Safety & Guardrails：敏感操作二次确认、参数审计、LLM 安全级别选择；离线回放与审计日志。

### F-Track：Jarvis UI/UX 重构（并行前端轨道）

> 与后端里程碑并行推进，不阻塞 M2-M4。

**目标**：打造专业的 Jarvis 风格界面，对话驱动，统一入口。

**产品定位**：
- Alice = 个人 Jarvis，不是"学习工具"
- 弱化学习痕迹，强调任务与洞察
- 对话是核心入口，一切操作可通过对话完成

**核心设计决策**：
- **对话即 Palette**：输入框 = 对话 + Command Palette 统一入口
  - 默认自然语言对话 → 走 AI
  - `/` 或 `Cmd+K` → 命令模式，快速操作
  - AI 返回可执行建议（点击即执行）
- **精简路由**：仅 `/`(对话)、`/library`(知识库)、`/settings`
- **统一知识库**：Library 合并视频/文档/笔记/链接，Video 详情作为 Drawer
- **洞察呈现**：Graph/Timeline 作为 Overlay/洞察卡，不是独立页面
- **三栏布局**：左导航 + 主画布(对话/库切换) + 右侧动态面板(引用/工具/确认)

**技术栈**：
- 保留 Next.js 15 + React 19 + Radix + Tailwind v4
- 引入 shadcn/ui 基础组件
- Framer Motion 克制动效
- Design Tokens 规范化

**分阶段落地**：
- **F1 设计基座**：调性定义、tokens、基础组件、Storybook
- **F2 核心页面**：Chat + Library + 右侧面板 + Command 模式
- **F3 扩展**：Overlay(Graph/Timeline)、移动端适配、动效打磨

**设计参考**：Perplexity（对话+引用）、Readwise（信息密度）、Linear（设计系统）、Raycast（Command）

**与后端依赖**：
- 需稳定 API 契约：`/videos`、`/agent`、`/knowledge`
- 新增：Agent 返回 `suggested_actions` 支持可执行建议

### M5：评测与自治（持续）
- Eval：基于 `alice/eval` 增加多步 Agent 回归集、工具调用金标、超时与异常覆盖。
- Autopilot：低风险场景允许自动执行/重试；高风险保留人类确认；配置化 SLA（超时、重试、并发度）。

---

## 近期优先级（执行提示）
- 完成 Phase 1 的安全与多租户修复后，再接线 Planner/Executor，避免循环在不安全基线上运行。
- 所有新特性配套测试（pytest + `pytest.mark.asyncio`），外部依赖需 mock。
- 控制平面/配置：统一从 `config/base/` 读取，LLM 通过 ControlPlane 获取，不直接实例化。
