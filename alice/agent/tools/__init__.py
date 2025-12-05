"""
Alice Agent Tools

本地工具和外部工具的定义与注册。
"""

from .basic import (
    EchoTool,
    CurrentTimeTool,
    SleepTool,
    GetTimelineSummaryTool,
    GetVideoSummaryTool,
    SearchVideosTool,
    get_basic_tools,
    register_basic_tools,
)

from .search_tools import (
    DeepWebResearchTool,
    register_search_tools,
)

__all__ = [
    # Basic tools
    "EchoTool",
    "CurrentTimeTool",
    "SleepTool",
    "GetTimelineSummaryTool",
    "GetVideoSummaryTool",
    "SearchVideosTool",
    # Search tools
    "DeepWebResearchTool",
    # Helpers
    "get_basic_tools",
    "register_basic_tools",
    "register_search_tools",
]
