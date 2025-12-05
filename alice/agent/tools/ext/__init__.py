"""
Alice Agent 扩展工具库

基于 strands-agents/tools 风格实现的通用工具集
"""

from .basic import (
    CalculatorTool,
    CurrentTimeTool,
    SleepTool,
    EnvironmentTool,
    JournalTool,
    get_basic_ext_tools,
    register_basic_ext_tools,
)

from .files import (
    FileReadTool,
    FileWriteTool,
    get_file_tools,
    register_file_tools,
)

from .http_web import (
    HttpRequestTool,
    TavilySearchTool,
    TavilyExtractTool,
    ExaSearchTool,
    ExaGetContentsTool,
    get_http_web_tools,
    register_http_web_tools,
)

from .rss_cron import (
    RssTool,
    CronTool,
    get_rss_cron_tools,
    register_rss_cron_tools,
)

# 高危工具单独导入，不默认暴露
# from .unsafe import get_unsafe_tools, register_unsafe_tools

__all__ = [
    # Basic
    "CalculatorTool",
    "CurrentTimeTool", 
    "SleepTool",
    "EnvironmentTool",
    "JournalTool",
    "get_basic_ext_tools",
    "register_basic_ext_tools",
    # Files
    "FileReadTool",
    "FileWriteTool",
    "get_file_tools",
    "register_file_tools",
    # HTTP/Web
    "HttpRequestTool",
    "TavilySearchTool",
    "TavilyExtractTool",
    "ExaSearchTool",
    "ExaGetContentsTool",
    "get_http_web_tools",
    "register_http_web_tools",
    # RSS/Cron
    "RssTool",
    "CronTool",
    "get_rss_cron_tools",
    "register_rss_cron_tools",
]


def register_all_ext_tools(router):
    """注册所有安全的扩展工具"""
    register_basic_ext_tools(router)
    register_file_tools(router)
    register_http_web_tools(router)
    register_rss_cron_tools(router)
