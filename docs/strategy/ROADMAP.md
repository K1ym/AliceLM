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

## 全局技术债清单

> 以下问题跨越多个模块，需要在各里程碑中逐步修复。

### P1 严重问题

| # | 类别 | 文件 | 问题 | 影响 | 归属 |
|---|------|------|------|------|------|
| T1 | 异步阻塞 | `video_service.py:37-85` | 新建 event loop + run_until_complete | 阻塞 FastAPI 事件循环，资源泄漏 | M1 |
| T2 | Token 预算 | `context_compressor.py`, `summarizer.py`, `conversations.py` | 字符数冒充 token 数 | 上下文可能超限或截断过度 | M2.5 |
| T3 | HTTP 客户端 | `video_service.py`, `watcher/*.py` | 未复用连接池，无重试策略 | 资源占用高，易挂死/被限流 | M1 |
| T4 | 时间戳 | `core.py`, `tool_executor.py`, `pipeline.py` | 混用 `now()` 和 `utcnow()`，naive datetime | 时区混乱，耗时计算不准 | M1 |
| T5 | 单例线程安全 | `qa.py`, `VideoProcessingQueue` | 全局单例无线程安全，生命周期不清 | 多线程下竞态或资源泄漏 | M1 |

### P2 重要问题

| # | 类别 | 文件 | 问题 | 影响 | 归属 |
|---|------|------|------|------|------|
| T6 | 魔数硬编码 | `context_compressor.py`, `summarizer.py`, `conversations.py` | 15000 字符、6 条消息、20k 等硬编码 | 随模型变更失效 | M2.5 |
| T7 | 索引缺失 | 新增 memory/graph/timeline 表 | 缺少 (tenant_id, scene, source_id) 复合索引 | 检索性能隐患 | M2.5 |
| T8 | 文件清理 | `pipeline.py`, `downloader.py` | 临时文件残留，异常分支不清理 | 磁盘增长 | M3 |
| T9 | 错误处理 | 多处 broad except | 仅日志无分类错误码/重试策略 | 排障困难 | M1 |
| T10 | API 不一致 | `knowledge.ts`, 部分 API | bvid 残留，与 source_type/source_id 规范不一致 | 前后端错位 | M1 |

### P3 优化项

| # | 类别 | 问题 | 归属 |
|---|------|------|------|
| T11 | 缓存缺失 | LLM/外部 API 调用无缓存，Prompt 无 cache | M4 |
| T12 | 观测缺失 | Context/RAG/Memory 无 metrics/trace | M3 |
| T13 | 分页缺失 | 部分列表接口无分页限制 | M3 |

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
- **技术债修复（T1/T3/T4/T5/T9/T10）**：
  - T1: 修复 `video_service.py` 异步阻塞，改为纯 async 实现
  - T3: 统一 HTTP 客户端，复用连接池，设定超时+重试策略
  - T4: 统一时间戳为 UTC，使用 timezone-aware datetime
  - T5: 重构全局单例，使用依赖注入/工厂模式
  - T9: 分类异常 + 错误码 + 可重试策略
  - T10: 清理 bvid 残留，统一 source_type/source_id
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

#### Phase 0：技术债清理（M2.5 第一阶段）

> ⚠️ **AliceMem 的第一步**：清理现有上下文管理的技术债，为新系统奠定正确基础。

**P0 致命问题（Week 1）**：

| # | 问题 | 文件 | 修复方式 |
|---|------|------|---------|
| 1 | 字符计数假装 Token 计数 | `context_compressor.py:92`<br>`conversations.py:220,225,261` | 集成 tiktoken，替换所有 `len(content)` |
| 2 | 硬编码 Magic Number | `conversations.py:33-34`<br>`context_compressor.py:16-17`<br>`context.py:82` | 移除硬编码，改为基于模型的动态配置 |
| 3 | 核心 RAG 功能空实现 | `alice/one/context.py:172-193` | 调用现有 `alice/rag/service.py`，填充 `_retrieve_from_rag/graph/timeline` |

**P1 严重问题（Week 2）**：

| # | 问题 | 文件 | 修复方式 |
|---|------|------|---------|
| 4 | 对话历史无 Token 预算 | `conversations.py:218` | 按 token 预算加载，不再 `limit=1000` |
| 5 | 压缩策略完全错误 | `conversations.py:225-236` | 基于 token 而非消息数，增加缓存 |
| 6 | get_message_count N+1 | `chat_service.py:133-135` | 改用 `COUNT(*)` 查询 |

**P2 重要问题（Week 3）**：

| # | 问题 | 文件 | 修复方式 |
|---|------|------|---------|
| 7 | 没有 tiktoken 依赖 | `pyproject.toml` | 添加 `tiktoken>=0.5.0` |
| 8 | 无 Prompt 缓存机制 | 全局 | 利用 Anthropic Prompt Caching |
| 9 | ChromaClient chunking 用字符数 | `chroma_client.py:245` | 用 tiktoken 切分 |
| 10 | 没有 token 使用监控 | 全局 | 添加 LLM 调用 metrics |

**验收标准**：
- [ ] `grep -r "len(content)" --include="*.py"` 返回 0 结果（token 相关场景）
- [ ] 所有上下文阈值从配置读取，无硬编码
- [ ] `_retrieve_from_rag()` 返回真实数据，非空列表
- [ ] 对话列表加载时间 < 200ms（修复 N+1）

---

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
| **Phase 0** (1-2周) | 技术债清理：tiktoken 集成、移除硬编码、修复空实现、N+1 查询 | 见上方验收标准清单 |
| **Phase 1** (1周) | Token Budget Manager + Recent Window | 上下文组装遵循 token 预算，无裸字符计数 |
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

### F-Track：Jarvis UI/UX 完全重构（并行前端轨道）

> ⚠️ **完全重构**：不是迭代优化，而是从零重建前端架构和设计系统。
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

**分阶段落地与排期**：

| Phase | 内容 | 时间 | 交付物 |
|-------|------|------|--------|
| **F0 设计准备** | Moodboard、调性定义、Figma 骨架、Design Tokens | 1 周 | 设计规范文档 + Figma 文件 |
| **F1 设计基座** | 基础组件库、Storybook、主题系统 | 1-2 周 | 可复用组件 + Storybook |
| **F2 核心页面** | Chat 主页 + Library 页 + 右侧面板 + Command 模式 | 2-3 周 | 3 个核心页面可用 |
| **F3 交互完善** | Overlay(Graph/Timeline)、洞察卡、Safety 确认流 | 1-2 周 | 完整交互流程 |
| **F4 打磨发布** | 移动端适配、动效打磨、可用性测试、性能优化 | 1-2 周 | 生产就绪 |

**总计：6-10 周**（与后端 M2-M4 并行）

**设计参考**：
- Perplexity（对话+引用并列）
- Readwise Reader（信息密度控制）
- Linear（设计系统一致性）
- Raycast（Command Palette 交互）
- ChatGPT Desktop（对话为主的布局）
- Arc Browser（极简导航）

**与后端依赖**：
- 需稳定 API 契约：`/videos`、`/agent`、`/knowledge`
- 新增：Agent 返回 `suggested_actions` 支持可执行建议
- 需 M3 完成：AgentRun/Step 可视化、确认流 API

**设计资源方案**（无专职设计师）：
1. 使用 v0/Galileo AI 生成 moodboard + 组件样稿
2. 基于 shadcn + 自定义 tokens 快速拼装高保真 wireframe
3. 可选：外包资深 UI/UX 设计师做核心流（Library/Video/Chat）的 Figma 稿

**风险与缓解**：
- 设计资源不足：优先核心 3 页，其余复用组件
- 后端 API 不稳定：约定 OpenAPI 契约，前端可 mock 开发
- 工作量膨胀：严格控制 Phase 边界，MVP 优先

### M5：评测与自治（持续）
- Eval：基于 `alice/eval` 增加多步 Agent 回归集、工具调用金标、超时与异常覆盖。
- Autopilot：低风险场景允许自动执行/重试；高风险保留人类确认；配置化 SLA（超时、重试、并发度）。

---

## 近期优先级（执行提示）

### 当前状态
- **PR #6** (feat/m1-agent-observability): Agent 可观测性扩展 + 文档更新，待合并
- **M1 进行中**: 安全/多租户/异常处理/技术债修复

### 下一步行动

**立即（本周）**：
1. ✅ 合并 PR #6 到 main
2. 🔄 开始 M1 技术债修复：T1(异步阻塞)、T4(时间戳统一)、T3(HTTP客户端)
3. 🔄 添加 tiktoken 依赖，为 M2.5 Phase 0 做准备

**短期（1-2 周）**：
1. 完成 M1 剩余任务：安全修复、多源迁移、异常规范化
2. 启动 M2.5 Phase 0：技术债清理（token 预算、RAG 空实现修复）
3. 启动 F-Track F0：设计准备（Moodboard、Design Tokens）

**中期（3-4 周）**：
1. M2：启用 Agent 主循环（TaskPlanner + ToolExecutor 接线）
2. M2.5 Phase 1-2：AliceMem Recent Window + Summary Buffer
3. F-Track F1-F2：设计基座 + 核心页面开发

### 并行轨道

```
Week 1-2    Week 3-4    Week 5-6    Week 7-8    Week 9-10
   │           │           │           │           │
   ├── M1 ─────┤           │           │           │
   │           ├── M2 ─────┤           │           │
   ├── M2.5 P0 ┼── P1-2 ───┼── P3-4 ───┤           │
   │           │           ├── M3 ─────┤           │
   │           │           │           ├── M4 ─────┤
   │           │           │           │           │
   ├── F0 ─────┼── F1-F2 ──┼── F2 ─────┼── F3 ─────┼── F4
   │           │           │           │           │
```

### 关键原则
- 完成 M1 安全修复后，再接线 Planner/Executor，避免循环在不安全基线上运行
- 所有新特性配套测试（pytest + `pytest.mark.asyncio`），外部依赖需 mock
- 控制平面/配置：统一从 `config/base/` 读取，LLM 通过 ControlPlane 获取
- 前端重构与后端并行，通过 API 契约解耦
