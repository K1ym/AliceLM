"""
搜索相关工具

提供深度 Web 搜索能力
"""

from typing import Dict, Any

from ..tool_router import AliceTool
from alice.search import SearchAgentService


class DeepWebResearchTool(AliceTool):
    """
    深度 Web 搜索工具
    
    对给定问题进行多步 Web 检索和多源信息综合
    """
    
    @property
    def name(self) -> str:
        return "deep_web_research"
    
    @property
    def description(self) -> str:
        return "对给定问题进行深度 Web 检索和多源信息综合。适用于需要查询最新信息、对比分析、或需要多个来源验证的问题。"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "需要在互联网上检索的问题（可以是自然语言）",
                },
                "max_steps": {
                    "type": "integer",
                    "description": "最多执行多少轮检索/抓取/聚合步骤",
                    "minimum": 1,
                    "maximum": 8,
                    "default": 4,
                },
            },
            "required": ["query"],
        }
    
    def __init__(self, search_agent: SearchAgentService = None):
        """
        Args:
            search_agent: SearchAgentService 实例，如果不提供则创建默认实例
        """
        self._search_agent = search_agent
    
    @property
    def search_agent(self) -> SearchAgentService:
        """延迟初始化 SearchAgentService"""
        if self._search_agent is None:
            self._search_agent = SearchAgentService()
        return self._search_agent
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行深度 Web 搜索
        
        Returns:
            结构化结果，包含 query, sub_queries, sources, answer
        """
        query: str = args.get("query", "")
        if not query:
            return {"error": "query 参数不能为空"}
        
        max_steps: int = int(args.get("max_steps", 4))
        
        result = await self.search_agent.run(
            query=query,
            user_context=None,
            max_steps=max_steps,
        )
        
        # 返回结构化结果，方便 Agent 在后续步骤继续引用
        return {
            "query": result.query,
            "sub_queries": result.sub_queries,
            "sources": [
                {
                    "url": s.url,
                    "title": s.title,
                    "snippet": s.snippet,
                    "content": s.content,
                    "score": s.score,
                }
                for s in result.sources
            ],
            "answer": result.answer,
        }


def register_search_tools(router, search_agent: SearchAgentService = None):
    """
    注册搜索相关工具
    
    Args:
        router: ToolRouter 实例
        search_agent: SearchAgentService 实例（可选）
    """
    router.register_tool(DeepWebResearchTool(search_agent))
