"""
StrategySelector + 各 Strategy 定义

职责：
- StrategySelector: 根据 AgentTask.scene 选择合适的执行策略
- Strategy 基类: 定义策略的通用接口
- 具体 Strategy: ChatStrategy / ResearchStrategy / TimelineStrategy 等
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from .types import AgentTask, Scene


class Strategy(ABC):
    """Strategy 抽象基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """策略名称"""
        pass
    
    @property
    @abstractmethod
    def allowed_tools(self) -> List[str]:
        """该策略允许使用的工具列表"""
        pass
    
    @abstractmethod
    def get_system_prompt_suffix(self) -> str:
        """返回该策略特有的 system prompt 补充"""
        pass


class ChatStrategy(Strategy):
    """对话策略 - 偏日常对话、解释和轻量问答"""
    
    @property
    def name(self) -> str:
        return "chat"
    
    @property
    def allowed_tools(self) -> List[str]:
        return [
            "ask_video",
            "search_videos",
            "get_video_summary",
            "current_time",
        ]
    
    def get_system_prompt_suffix(self) -> str:
        return "你是一个友好的助手，专注于帮助用户理解和回顾他们看过的视频内容。"


class ResearchStrategy(Strategy):
    """研究策略 - 偏深度检索 / 多轮推理，启用 deep_web_research"""
    
    @property
    def name(self) -> str:
        return "research"
    
    @property
    def allowed_tools(self) -> List[str]:
        return [
            "ask_video",
            "search_videos",
            "search_graph",
            "deep_web_research",
            "generate_report",
            "current_time",
        ]
    
    def get_system_prompt_suffix(self) -> str:
        return (
            "你是一个深度研究助手，善于结合用户的知识库和互联网信息进行综合分析。"
            "当问题需要查阅最新信息时，优先调用 deep_web_research。"
        )


class TimelineStrategy(Strategy):
    """时间线策略 - 偏「自我变化 / 学习轨迹」类问题"""
    
    @property
    def name(self) -> str:
        return "timeline"
    
    @property
    def allowed_tools(self) -> List[str]:
        return [
            "timeline_query",
            "get_timeline_summary",
            "search_videos",
            "current_time",
        ]
    
    def get_system_prompt_suffix(self) -> str:
        return (
            "你关注用户的学习轨迹和成长变化，"
            "善于从时间线事件中发现规律和提供反思。"
        )


class StrategySelector:
    """策略选择器"""
    
    def __init__(self):
        self._strategies = {
            Scene.CHAT: ChatStrategy(),
            Scene.RESEARCH: ResearchStrategy(),
            Scene.TIMELINE: TimelineStrategy(),
            # 其他场景暂时映射到 ChatStrategy
            Scene.LIBRARY: ChatStrategy(),
            Scene.VIDEO: ChatStrategy(),
            Scene.GRAPH: ResearchStrategy(),
            Scene.TASKS: ChatStrategy(),
            Scene.CONSOLE: ResearchStrategy(),
        }
    
    def select(self, task: AgentTask) -> Strategy:
        """根据 AgentTask 选择合适的策略"""
        return self._strategies.get(task.scene, ChatStrategy())
