"""
RSS / Cron 工具

包含：rss, cron
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import httpx

from alice.agent.tool_router import AliceTool

logger = logging.getLogger(__name__)


class RssTool(AliceTool):
    """
    RSS 订阅工具
    
    获取 RSS/Atom feed 内容
    """
    
    @property
    def name(self) -> str:
        return "rss"
    
    @property
    def description(self) -> str:
        return "获取 RSS/Atom 订阅源的最新内容"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "feed_url": {
                    "type": "string",
                    "description": "RSS/Atom feed URL",
                },
                "max_items": {
                    "type": "integer",
                    "description": "返回的最大条目数",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50,
                },
                "include_content": {
                    "type": "boolean",
                    "description": "是否包含完整内容",
                    "default": False,
                },
            },
            "required": ["feed_url"],
        }
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        feed_url = args.get("feed_url", "")
        max_items = args.get("max_items", 10)
        include_content = args.get("include_content", False)
        
        if not feed_url:
            return {"error": "feed_url 参数不能为空"}
        
        try:
            # 尝试导入 feedparser
            try:
                import feedparser
            except ImportError:
                return {"error": "feedparser 未安装，请运行: pip install feedparser"}
            
            # 获取 feed
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(feed_url)
                response.raise_for_status()
                content = response.text
            
            # 解析 feed
            feed = feedparser.parse(content)
            
            if feed.bozo and not feed.entries:
                return {"error": f"解析失败: {feed.bozo_exception}"}
            
            # 提取条目
            items = []
            for entry in feed.entries[:max_items]:
                item = {
                    "title": entry.get("title", "Untitled"),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", entry.get("updated", "")),
                    "author": entry.get("author", ""),
                }
                
                if include_content:
                    # 获取内容
                    content = ""
                    if "content" in entry:
                        if isinstance(entry.content, list) and entry.content:
                            content = entry.content[0].get("value", "")
                    if not content and "summary" in entry:
                        content = entry.summary
                    if not content and "description" in entry:
                        content = entry.description
                    
                    # 简单清理 HTML
                    import re
                    content = re.sub(r'<[^>]+>', '', content)
                    content = content[:2000]  # 截断
                    item["content"] = content
                
                items.append(item)
            
            return {
                "feed_title": feed.feed.get("title", ""),
                "feed_link": feed.feed.get("link", ""),
                "items": items,
                "count": len(items),
            }
            
        except httpx.TimeoutException:
            return {"error": "请求超时"}
        except Exception as e:
            return {"error": f"获取 RSS 失败: {str(e)}"}


class CronTool(AliceTool):
    """
    Cron 表达式工具
    
    解析 cron 表达式，返回下次触发时间
    """
    
    @property
    def name(self) -> str:
        return "cron"
    
    @property
    def description(self) -> str:
        return "解析 cron 表达式，返回未来的触发时间"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Cron 表达式，如 '0 9 * * 1-5' (工作日 9 点)",
                },
                "count": {
                    "type": "integer",
                    "description": "返回未来多少次触发时间",
                    "default": 5,
                    "minimum": 1,
                    "maximum": 20,
                },
            },
            "required": ["expression"],
        }
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        expression = args.get("expression", "")
        count = args.get("count", 5)
        
        if not expression:
            return {"error": "expression 参数不能为空"}
        
        try:
            # 尝试导入 croniter
            try:
                from croniter import croniter
            except ImportError:
                return {"error": "croniter 未安装，请运行: pip install croniter"}
            
            # 解析并获取下次触发时间
            base = datetime.now()
            cron = croniter(expression, base)
            
            next_times = []
            for _ in range(count):
                next_time = cron.get_next(datetime)
                next_times.append({
                    "datetime": next_time.isoformat(),
                    "formatted": next_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "weekday": next_time.strftime("%A"),
                })
            
            return {
                "expression": expression,
                "next_times": next_times,
                "count": len(next_times),
            }
            
        except Exception as e:
            return {"error": f"解析 cron 表达式失败: {str(e)}"}


def get_rss_cron_tools():
    """获取所有 RSS/Cron 工具实例"""
    return [
        RssTool(),
        CronTool(),
    ]


def register_rss_cron_tools(router):
    """注册 RSS/Cron 工具到 ToolRouter"""
    for tool in get_rss_cron_tools():
        router.register_tool(tool)
