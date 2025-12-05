"""
HTTP 搜索客户端

提供统一的 Web 搜索接口，支持多种搜索后端。
"""

import logging
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class WebSearchResult:
    """Web 搜索结果"""
    url: str
    title: str
    snippet: str
    score: Optional[float] = None


class SearchProvider(ABC):
    """搜索提供者抽象基类"""
    
    @abstractmethod
    async def search(self, query: str, top_k: int = 5) -> List[WebSearchResult]:
        """执行搜索"""
        pass


class TavilySearchProvider(SearchProvider):
    """Tavily 搜索提供者"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ALICE_SEARCH__TAVILY_API_KEY")
        self.base_url = "https://api.tavily.com"
    
    async def search(self, query: str, top_k: int = 5) -> List[WebSearchResult]:
        if not self.api_key:
            logger.warning("Tavily API key not configured")
            return []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/search",
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "search_depth": "basic",
                        "max_results": top_k,
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("results", []):
                    results.append(WebSearchResult(
                        url=item.get("url", ""),
                        title=item.get("title", ""),
                        snippet=item.get("content", ""),
                        score=item.get("score"),
                    ))
                return results
                
        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return []


class DuckDuckGoSearchProvider(SearchProvider):
    """DuckDuckGo 搜索提供者（无需 API key）"""
    
    async def search(self, query: str, top_k: int = 5) -> List[WebSearchResult]:
        try:
            # 使用 DuckDuckGo HTML 搜索
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": query},
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                    }
                )
                response.raise_for_status()
                
                # 简单解析 HTML 结果
                from html.parser import HTMLParser
                
                results = []
                
                class DDGParser(HTMLParser):
                    def __init__(self):
                        super().__init__()
                        self.in_result = False
                        self.current_result = {}
                        self.current_tag = None
                        
                    def handle_starttag(self, tag, attrs):
                        attrs_dict = dict(attrs)
                        if tag == "a" and "result__a" in attrs_dict.get("class", ""):
                            self.in_result = True
                            self.current_result = {
                                "url": attrs_dict.get("href", ""),
                                "title": "",
                                "snippet": ""
                            }
                            self.current_tag = "title"
                        elif self.in_result and tag == "a" and "result__snippet" in attrs_dict.get("class", ""):
                            self.current_tag = "snippet"
                            
                    def handle_data(self, data):
                        if self.in_result and self.current_tag:
                            self.current_result[self.current_tag] += data.strip()
                            
                    def handle_endtag(self, tag):
                        if tag == "div" and self.in_result:
                            if self.current_result.get("url") and self.current_result.get("title"):
                                results.append(WebSearchResult(
                                    url=self.current_result["url"],
                                    title=self.current_result["title"],
                                    snippet=self.current_result.get("snippet", ""),
                                ))
                            self.in_result = False
                            self.current_result = {}
                            self.current_tag = None
                
                parser = DDGParser()
                parser.feed(response.text)
                
                return results[:top_k]
                
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []


class MockSearchProvider(SearchProvider):
    """模拟搜索提供者（用于测试）"""
    
    async def search(self, query: str, top_k: int = 5) -> List[WebSearchResult]:
        return [
            WebSearchResult(
                url=f"https://example.com/result/{i}",
                title=f"Search Result {i} for: {query[:30]}",
                snippet=f"This is a mock search result snippet for query: {query}",
                score=1.0 - i * 0.1,
            )
            for i in range(min(top_k, 3))
        ]


def get_search_provider() -> SearchProvider:
    """获取配置的搜索提供者"""
    provider_name = os.getenv("ALICE_SEARCH__PROVIDER", "mock").lower()
    
    if provider_name == "tavily":
        return TavilySearchProvider()
    elif provider_name == "duckduckgo":
        return DuckDuckGoSearchProvider()
    else:
        logger.info("Using mock search provider (set ALICE_SEARCH__PROVIDER to 'tavily' or 'duckduckgo' for real search)")
        return MockSearchProvider()
