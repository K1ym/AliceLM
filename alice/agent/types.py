"""
Alice Agent 核心数据类型定义

这些数据类贯穿 Alice One + Agent 各模块，是实现时的"合同"。
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


# ============================================================
# 场景与任务
# ============================================================

class Scene(str, Enum):
    """Agent 支持的场景类型"""
    CHAT = "chat"
    RESEARCH = "research"
    TIMELINE = "timeline"
    LIBRARY = "library"
    VIDEO = "video"
    GRAPH = "graph"
    TASKS = "tasks"
    CONSOLE = "console"


@dataclass
class AgentTask:
    """Agent 的统一输入契约"""
    tenant_id: str
    scene: Scene                          # 当前场景
    query: str                            # 用户输入
    user_id: Optional[str] = None
    video_id: Optional[int] = None        # 关联视频（若有）
    selection: Optional[str] = None       # 用户选中的文本
    extra_context: Dict[str, Any] = field(default_factory=dict)


# ============================================================
# Agent 运行状态
# ============================================================

class AgentRunState(str, Enum):
    """
    Agent 执行过程的状态
    
    生命周期：IDLE -> RUNNING -> (FINISHED | ERROR)
    """
    IDLE = "idle"           # 空闲，等待任务
    RUNNING = "running"     # 执行中
    FINISHED = "finished"   # 正常完成
    ERROR = "error"         # 执行出错


class PlanStepState(str, Enum):
    """计划步骤的状态"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"

    @classmethod
    def get_active_states(cls) -> List[str]:
        return [cls.NOT_STARTED.value, cls.IN_PROGRESS.value]

    @classmethod
    def get_status_marks(cls) -> Dict[str, str]:
        return {
            cls.COMPLETED.value: "[✓]",
            cls.IN_PROGRESS.value: "[→]",
            cls.BLOCKED.value: "[!]",
            cls.NOT_STARTED.value: "[ ]",
        }


# ============================================================
# 工具执行相关
# ============================================================

@dataclass
class ToolResult:
    """
    工具执行结果（单次调用的返回）
    
    用于 ToolRouter.execute() 的返回值
    """
    success: bool                         # 是否成功
    output: Any = None                    # 原始输出
    summary: Optional[str] = None         # 摘要（供 LLM 使用）
    error: Optional[str] = None           # 错误信息（失败时）
    
    def __str__(self) -> str:
        if self.error:
            return f"Error: {self.error}"
        return self.summary or str(self.output) or "No output"


@dataclass
class ToolTrace:
    """
    工具调用追踪（完整的调用记录）
    
    包含输入、输出、时间等，用于调试和回放
    """
    tool_name: str
    tool_args: Dict[str, Any]
    result: ToolResult
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: Optional[datetime] = None
    
    @property
    def duration_ms(self) -> Optional[float]:
        """执行耗时（毫秒）"""
        if self.finished_at:
            return (self.finished_at - self.started_at).total_seconds() * 1000
        return None


# ============================================================
# Agent 执行步骤与结果
# ============================================================

@dataclass
class AgentCitation:
    """引用来源"""
    type: str                             # video / concept / timeline / web
    id: str
    title: str
    snippet: str
    url: Optional[str] = None


@dataclass
class AgentStep:
    """Agent 执行的单个步骤（用于调试 / 回放）"""
    step_idx: int
    thought: str                          # LLM 的思考
    tool_name: Optional[str] = None
    tool_args: Optional[Dict] = None
    observation: Optional[str] = None
    error: Optional[str] = None
    tool_trace: Optional[ToolTrace] = None  # 工具执行追踪


@dataclass
class AgentPlan:
    """Agent 任务规划"""
    steps: List[str] = field(default_factory=list)
    current_step: int = 0


@dataclass
class AgentResult:
    """Agent 的统一输出契约"""
    answer: str
    citations: List[AgentCitation] = field(default_factory=list)
    steps: List[AgentStep] = field(default_factory=list)        # 执行步骤
    tool_traces: List[ToolTrace] = field(default_factory=list)  # 工具调用追踪
    token_usage: Optional[Dict[str, int]] = None
