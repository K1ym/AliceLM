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
- **上下文与记忆不足**：RAG/Graph/Timeline/Memory 未整合到循环，工具无法带上下文自适应。
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

### M3：人机协同与可视化（2 周）
- API：step 确认 `/agent/runs/{run_id}/steps/{step_id}/confirm`，任务中心 `/tasks` 列表/重试/取消，记忆中心 `/memory/insights` CRUD。
- 前端：AgentRunPanel 展示步骤/工具/日志，支持流式与分页；高风险步骤确认 UI；任务中心/记忆中心 MVP。
- Observability：step trace 持久化，超时/熔断/重试策略落地，基础 metrics（成功率、平均步数）。

### M4：Jarvis 化能力（3–4 周）
- 个性化：UserModelService（概念掌握度/风格/偏好）+ Context 个性化 prompt；记忆中心回流到检索/工具。
- 并行与策略：简单节点图（LangGraph 风格）支持并行工具与条件路由；Research/Timeline 策略可自适应选工具包。
- Safety & Guardrails：敏感操作二次确认、参数审计、LLM 安全级别选择；离线回放与审计日志。

### M5：评测与自治（持续）
- Eval：基于 `alice/eval` 增加多步 Agent 回归集、工具调用金标、超时与异常覆盖。
- Autopilot：低风险场景允许自动执行/重试；高风险保留人类确认；配置化 SLA（超时、重试、并发度）。

---

## 近期优先级（执行提示）
- 完成 Phase 1 的安全与多租户修复后，再接线 Planner/Executor，避免循环在不安全基线上运行。
- 所有新特性配套测试（pytest + `pytest.mark.asyncio`），外部依赖需 mock。
- 控制平面/配置：统一从 `config/base/` 读取，LLM 通过 ControlPlane 获取，不直接实例化。
