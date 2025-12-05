"""
HTTP / Web 搜索工具

包含：http_request, tavily_search, exa_search 等
"""

import logging
import os
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse

import httpx

from alice.agent.tool_router import AliceTool

logger = logging.getLogger(__name__)


# URL 白名单（可选，默认允许所有 HTTPS）
ALLOWED_DOMAINS = os.environ.get("ALICE_ALLOWED_DOMAINS", "").split(",")
BLOCKED_DOMAINS = ["localhost", "127.0.0.1", "0.0.0.0", "internal"]


def is_url_allowed(url: str) -> bool:
    """检查 URL 是否允许访问"""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        
        # 阻止访问内部地址
        for blocked in BLOCKED_DOMAINS:
            if blocked in host:
                return False
        
        # 如果配置了白名单，只允许白名单中的域名
        if ALLOWED_DOMAINS and ALLOWED_DOMAINS[0]:
            return any(domain in host for domain in ALLOWED_DOMAINS)
        
        return True
    except:
        return False


class HttpRequestTool(AliceTool):
    """
    HTTP 请求工具
    
    支持 GET/POST 等基本请求
    """
    
    TIMEOUT = 30.0
    MAX_RESPONSE_SIZE = 1024 * 1024  # 1MB
    
    @property
    def name(self) -> str:
        return "http_request"
    
    @property
    def description(self) -> str:
        return "发送 HTTP 请求到指定 URL"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                    "description": "HTTP 方法",
                    "default": "GET",
                },
                "url": {
                    "type": "string",
                    "description": "请求 URL",
                },
                "headers": {
                    "type": "object",
                    "description": "请求头",
                },
                "body": {
                    "type": "string",
                    "description": "请求体（POST/PUT 等）",
                },
                "json_body": {
                    "type": "object",
                    "description": "JSON 请求体",
                },
                "timeout": {
                    "type": "number",
                    "description": "超时秒数",
                    "default": 30,
                },
            },
            "required": ["url"],
        }
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        method = args.get("method", "GET").upper()
        url = args.get("url", "")
        headers = args.get("headers", {})
        body = args.get("body")
        json_body = args.get("json_body")
        timeout = min(args.get("timeout", self.TIMEOUT), 60)
        
        if not url:
            return {"error": "url 参数不能为空"}
        
        # 安全检查
        if not is_url_allowed(url):
            return {"error": f"不允许访问该 URL: {url}"}
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                kwargs = {"headers": headers}
                if body:
                    kwargs["content"] = body
                if json_body:
                    kwargs["json"] = json_body
                
                response = await client.request(method, url, **kwargs)
                
                # 限制响应大小
                content = response.text[:self.MAX_RESPONSE_SIZE]
                truncated = len(response.text) > self.MAX_RESPONSE_SIZE
                
                return {
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "content": content,
                    "content_length": len(response.text),
                    "truncated": truncated,
                }
        except httpx.TimeoutException:
            return {"error": f"请求超时 ({timeout}s)"}
        except Exception as e:
            return {"error": f"请求失败: {str(e)}"}


class TavilySearchTool(AliceTool):
    """
    Tavily 搜索工具
    
    使用 Tavily API 进行 Web 搜索
    """
    
    @property
    def name(self) -> str:
        return "tavily_search"
    
    @property
    def description(self) -> str:
        return "使用 Tavily 进行 Web 搜索，返回结构化搜索结果"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询",
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大结果数",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 10,
                },
                "search_depth": {
                    "type": "string",
                    "enum": ["basic", "advanced"],
                    "description": "搜索深度",
                    "default": "basic",
                },
            },
            "required": ["query"],
        }
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        api_key = os.environ.get("ALICE_SEARCH__TAVILY_API_KEY")
        if not api_key:
            return {"error": "Tavily API key 未配置 (ALICE_SEARCH__TAVILY_API_KEY)"}
        
        query = args.get("query", "")
        max_results = args.get("max_results", 5)
        search_depth = args.get("search_depth", "basic")
        
        if not query:
            return {"error": "query 参数不能为空"}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": api_key,
                        "query": query,
                        "search_depth": search_depth,
                        "max_results": max_results,
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("results", []):
                    results.append({
                        "url": item.get("url", ""),
                        "title": item.get("title", ""),
                        "content": item.get("content", ""),
                        "score": item.get("score"),
                    })
                
                return {
                    "query": query,
                    "results": results,
                    "count": len(results),
                }
        except Exception as e:
            return {"error": f"Tavily 搜索失败: {str(e)}"}


class TavilyExtractTool(AliceTool):
    """
    Tavily 内容提取工具
    
    从 URL 提取结构化内容
    """
    
    @property
    def name(self) -> str:
        return "tavily_extract"
    
    @property
    def description(self) -> str:
        return "使用 Tavily 从 URL 提取内容"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "urls": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "要提取内容的 URL 列表",
                },
            },
            "required": ["urls"],
        }
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        api_key = os.environ.get("ALICE_SEARCH__TAVILY_API_KEY")
        if not api_key:
            return {"error": "Tavily API key 未配置"}
        
        urls = args.get("urls", [])
        if not urls:
            return {"error": "urls 参数不能为空"}
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.tavily.com/extract",
                    json={
                        "api_key": api_key,
                        "urls": urls[:5],  # 限制最多 5 个 URL
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                return {
                    "results": data.get("results", []),
                    "failed_urls": data.get("failed_results", []),
                }
        except Exception as e:
            return {"error": f"Tavily 提取失败: {str(e)}"}


class ExaSearchTool(AliceTool):
    """
    Exa 搜索工具
    
    使用 Exa API 进行语义搜索
    """
    
    @property
    def name(self) -> str:
        return "exa_search"
    
    @property
    def description(self) -> str:
        return "使用 Exa 进行语义 Web 搜索"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索查询",
                },
                "num_results": {
                    "type": "integer",
                    "description": "结果数量",
                    "default": 5,
                },
                "use_autoprompt": {
                    "type": "boolean",
                    "description": "是否自动优化查询",
                    "default": True,
                },
            },
            "required": ["query"],
        }
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        api_key = os.environ.get("ALICE_SEARCH__EXA_API_KEY")
        if not api_key:
            return {"error": "Exa API key 未配置 (ALICE_SEARCH__EXA_API_KEY)"}
        
        query = args.get("query", "")
        num_results = args.get("num_results", 5)
        use_autoprompt = args.get("use_autoprompt", True)
        
        if not query:
            return {"error": "query 参数不能为空"}
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.exa.ai/search",
                    headers={"x-api-key": api_key},
                    json={
                        "query": query,
                        "numResults": num_results,
                        "useAutoprompt": use_autoprompt,
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                results = []
                for item in data.get("results", []):
                    results.append({
                        "url": item.get("url", ""),
                        "title": item.get("title", ""),
                        "score": item.get("score"),
                        "published_date": item.get("publishedDate"),
                    })
                
                return {
                    "query": query,
                    "results": results,
                    "count": len(results),
                }
        except Exception as e:
            return {"error": f"Exa 搜索失败: {str(e)}"}


class ExaGetContentsTool(AliceTool):
    """
    Exa 内容获取工具
    """
    
    @property
    def name(self) -> str:
        return "exa_get_contents"
    
    @property
    def description(self) -> str:
        return "使用 Exa 获取 URL 的内容"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Exa 搜索返回的结果 ID 列表",
                },
            },
            "required": ["ids"],
        }
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        api_key = os.environ.get("ALICE_SEARCH__EXA_API_KEY")
        if not api_key:
            return {"error": "Exa API key 未配置"}
        
        ids = args.get("ids", [])
        if not ids:
            return {"error": "ids 参数不能为空"}
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "https://api.exa.ai/contents",
                    headers={"x-api-key": api_key},
                    json={
                        "ids": ids[:10],
                        "text": True,
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                return {"results": data.get("results", [])}
        except Exception as e:
            return {"error": f"Exa 获取内容失败: {str(e)}"}


def get_http_web_tools():
    """获取所有 HTTP/Web 工具实例"""
    return [
        HttpRequestTool(),
        TavilySearchTool(),
        TavilyExtractTool(),
        ExaSearchTool(),
        ExaGetContentsTool(),
    ]


def register_http_web_tools(router):
    """注册 HTTP/Web 工具到 ToolRouter"""
    for tool in get_http_web_tools():
        router.register_tool(tool)
