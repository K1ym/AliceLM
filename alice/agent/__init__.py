"""
Alice Agent 引擎

核心组件：
- AliceAgentCore: 统一入口
- StrategySelector: 策略选择器
- TaskPlanner: 任务规划器
- ToolExecutor: ReAct 执行器
- ToolRouter: 工具路由器
"""

from .types import (
    Scene,
    AgentTask,
    AgentResult,
    AgentStep,
    AgentPlan,
    AgentCitation,
    AgentRunState,
    PlanStepState,
    ToolResult,
    ToolTrace,
)
from .core import AliceAgentCore, run_agent_task
from .strategy import Strategy, StrategySelector, ChatStrategy, ResearchStrategy, TimelineStrategy
from .task_planner import TaskPlanner
from .tool_executor import ToolExecutor
from .tool_router import ToolRouter, AliceTool, McpBackedTool
from .permissions import ToolVisibilityPolicy, UserRole, get_allowed_tools_for_context
from .run_logger import AgentRunLogger, AgentRunLog, get_agent_run_logger, log_agent_run

__all__ = [
    # Types
    "Scene",
    "AgentTask",
    "AgentResult",
    "AgentStep",
    "AgentPlan",
    "AgentCitation",
    "AgentRunState",
    "PlanStepState",
    "ToolResult",
    "ToolTrace",
    # Core
    "AliceAgentCore",
    "run_agent_task",
    # Strategy
    "Strategy",
    "StrategySelector",
    "ChatStrategy",
    "ResearchStrategy",
    "TimelineStrategy",
    # Components
    "TaskPlanner",
    "ToolExecutor",
    "ToolRouter",
    "AliceTool",
    "McpBackedTool",
    # Permissions
    "ToolVisibilityPolicy",
    "UserRole",
    "get_allowed_tools_for_context",
    # Logging
    "AgentRunLogger",
    "AgentRunLog",
    "get_agent_run_logger",
    "log_agent_run",
]
