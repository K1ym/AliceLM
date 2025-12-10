# 第三方能力迁移计划（Apache 许可源）

> 目标：在保持 ACE 四层架构与命名/安全规范的前提下，将第三方项目（mindsearch/openmanus/gemini_cli/strands）中的有价值能力迁入 Alice 代码库。所有迁移代码必须改名、对齐字段（source_type/source_id + tenant_id/user_id）、走 ControlPlane 配置、避免敏感日志，并使用 `alice.errors`。

## 优先级
1) 搜索/规划（mindsearch）——补齐 deep_web_research 能力，接入 ReAct 循环。
2) 执行/状态（openmanus）——借鉴终止/超时/日志格式，完善 TaskPlanner/ToolExecutor + StateCore。
3) MCP 交互（gemini_cli）——改进 MCP 工具注册与流式输出体验。
4) 通用工具（strands_agents_tools）——继续迁移实用工具，保持 AliceTool 规范与安全级别。

## 路径与目标文件
- mindsearch → `alice/search/search_agent.py`（新增）：SearchAgentService + SearchPlan/SearchStep，封装为 `deep_web_research` Tool。依赖：ControlPlane 模型、HTTP 抓取、聚合摘要。
- openmanus → `alice/agent/tool_executor.py` / `alice/agent/task_planner.py`：终止/超时/日志格式/step trace；`alice/agent/state.py`（待建）实现 StateCore（session mode/active_plan/短期记忆）。
- gemini_cli → `alice/agent/mcp_client.py` / `alice/agent/tool_router.py`：MCP 工具注册健壮性、流式输出/重连。
- strands → `alice/agent/tools/ext/`：继续迁移 HTTP/文件/搜索等工具，增加安全级别/审计字段。

## 下一次工作第一步（建议）
在 `alice/search/search_agent.py` 编写 mindsearch 风格的搜索规划与抓取聚合：
1. 新建 `alice/search/search_agent.py`，定义 `SearchAgentService`（plan → fan-out search → summarize → aggregate），工具名 `deep_web_research`。
2. 使用 ControlPlane 取模型，HTTP 抓取用 httpx；字段统一 `source_type/source_id`，注入 tenant_id/user_id。
3. 提供 ToolRouter 注册函数，返回 AliceTool schema；添加基础单测（pytest, asyncio）mock httpx/LLM。

## 迁移检查表
- 命名：不保留第三方类/函数名，对齐 Alice 命名。
- 字段：`source_type`+`source_id`；tenant_id/user_id 注入；无 `bvid`。
- 错误/日志：使用 `alice.errors`；不记录 key/token。
- 配置：模型/提示/工具配置走 ControlPlane + config/base。
- 安全：工具标注安全级别，必要时 requires_user_confirm；日志有 tool_trace，支持超时/终止。
- 版权：文件头可注明来源（Apache 2.0），对外接口/日志不出现第三方项目名。
