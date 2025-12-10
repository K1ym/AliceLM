# ACE 对齐指南（四层架构 ↔ Alice 现状）

> 目的：把《Alice 认知引擎 (ACE) - 创世法典》的四层哲学落到当前代码与路线图，明确已迁移/可迁移的第三方能力（Apache 许可），并给出迁移适配规则。

## 1. 四层映射与缺口

| ACE 层 | 含义 | 当前状态 | 缺口/优先事项 |
| --- | --- | --- | --- |
| 层 I 感知交互（Gateway/API） | 统一入口，安全网关 | FastAPI + MCP 入口，AgentTask 统一契约 | 入口状态仲裁（基于 StateCore）、高风险确认流、旧路由清理 |
| 层 II 认知核心（StateCore/Planner/Executor/Reflector） | 状态机 + 规划 + 执行 + 反思 | `TaskPlanner`/`ToolExecutor` 已实现但未接线；无 StateCore/反思/回放 | 接线 Planner+Executor；新增 StateCore（session mode/active_plan/短期记忆）；微反思/宏反思；超时/终止/确认 |
| 层 III 能力支撑（LLM 抽象/Toolbox/Prompt） | 模型抽象、工具箱、提示引擎 | ControlPlane 已有；工具：本地+搜索+扩展（已迁 strands 部分）；Prompt 已配置 | 工具安全级别/审计；作用域与租户注入；补充通用工具；Prompt/模型选择与策略联动 |
| 层 IV 存在基础（Identity/Ethics/Memory/Resource） | 人格、伦理、记忆矩阵、资源/安全 | Identity/ContextAssembler 半成品；记忆/伦理/资源监控缺失；安全债未清 | 记忆中心 + UserModel；日志脱敏/API Key 加密/RBAC；资源/速率/熔断监控；安全确认策略 |

## 2. 第三方“零件”对齐（Apache，可复制改名）

| 来源 | 现状 | 可迁移内容 | 适配要求 |
| --- | --- | --- | --- |
| strands_agents_tools | 已部分迁入 `alice/agent/tools/ext/*` | HTTP 请求、搜索、文件、RSS、计算器等通用工具 | 转为 `AliceTool`；参数注入租户/用户；安全级别/审计；无敏感日志 |
| mindsearch | 未迁 | 多子 query 搜索规划、抓取、聚合（可做 `deep_web_research`） | 重写/拷贝为 `alice/search/search_agent.py`；控制平面模型；source_type/source_id |
| openmanus | 未迁 | ReAct 循环/执行日志/状态机参考 | 提炼终止/超时/日志格式，接到 `TaskPlanner`/`ToolExecutor` |
| gemini_cli | 未迁 | MCP 客户端/工具注册、流式输出模式 | 用于强化 MCP 连接与流式体验；保持 ToolRouter 规范 |

## 3. 迁移/拷贝硬规则
- 命名与数据：统一使用 `source_type`+`source_id`；租户/用户必须注入；禁止引入 `bvid`。
- 错误与安全：用 `alice.errors`；日志不含 key/token；工具标注安全级别并接入审计/确认。
- 配置与模型：LLM/服务必须通过 ControlPlane 与 `config/base/`，禁止直接实例化 SDK。
- 工具与状态：对齐 `AliceTool`/`ToolRouter` 接口；Planner/Executor 接入 StateCore（模式/超时/终止）。
- 版权：保留源引用注释（Apache），但禁止在对外接口/日志中出现第三方项目名。

## 4. 下一步建议（按层落地）
1) 层 II：接线 `TaskPlanner`+`ToolExecutor`，加入 StateCore（Redis/DB），实现微反思/终止/超时/确认；tool_trace 持久化。  
2) 层 III：再迁 strands 的实用工具（HTTP/文件/搜索）并加安全级别；改进 MCP 连接（参考 gemini_cli）。  
3) 层 IV：启动记忆中心 + UserModel；补 `operations/SECURITY.md`（RBAC/密钥/日志脱敏）与 `operations/RUNBOOK.md`。  
4) 层 I：入口按 StateCore 仲裁并串联高风险确认流；清理旧路由。  
