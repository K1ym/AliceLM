"""
Alice Search - 深度 Web 搜索服务

核心组件：
- SearchAgentService: 多子查询 + 多路搜索 + 聚合回答
"""

from .search_agent import SearchAgentService, SearchAgentResult, SearchSource
from .http_client import (
    SearchProvider, 
    TavilySearchProvider, 
    DuckDuckGoSearchProvider,
    MockSearchProvider,
    get_search_provider,
)

__all__ = [
    # 核心服务
    "SearchAgentService",
    "SearchAgentResult",
    "SearchSource",
    # 搜索提供者
    "SearchProvider",
    "TavilySearchProvider",
    "DuckDuckGoSearchProvider",
    "MockSearchProvider",
    "get_search_provider",
]
