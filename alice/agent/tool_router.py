"""
ToolRouter - 工具路由器

职责：
- 管理所有可用工具（本地 + MCP）
- list_tool_schemas: 返回当前场景/策略可用的工具 schema
- execute: 分发工具调用到对应的 handler

"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session

from .types import ToolResult
from .mcp_client import McpClient, McpToolDescription, McpRegistry, MockMcpClient

logger = logging.getLogger(__name__)


class AliceTool(ABC):
    """工具抽象基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """工具参数 JSON Schema"""
        pass
    
    @abstractmethod
    async def run(self, args: Dict[str, Any]) -> Any:
        """执行工具"""
        pass
    
    def to_schema(self) -> Dict[str, Any]:
        """转换为 OpenAI function calling 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }


class McpBackedTool(AliceTool):
    """
    MCP 工具包装器
    
    将远程 MCP 工具包装为 AliceTool，统一接口
    """
    
    def __init__(
        self,
        client: McpClient,
        tool_name: str,
        tool_description: str,
        tool_parameters: Dict[str, Any],
        server_name: str,
    ):
        self._client = client
        self._name = tool_name
        self._description = tool_description
        self._parameters = tool_parameters
        self._server_name = server_name
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def description(self) -> str:
        return f"{self._description} (via MCP: {self._server_name})"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return self._parameters
    
    async def run(self, args: Dict[str, Any]) -> Any:
        result = await self._client.call_tool(self._name, args)
        if result.success:
            return result.content
        else:
            raise RuntimeError(f"MCP tool error: {result.error}")


class ToolRouter:
    """
    工具路由器
    
    统一管理本地工具和 MCP 工具的注册与调用
    """
    
    def __init__(self):
        self._local_tools: Dict[str, AliceTool] = {}
        self._mcp_tools: Dict[str, McpBackedTool] = {}
        self._mcp_registry: Optional[McpRegistry] = None
    
    @classmethod
    def create_with_basic_tools(cls, db: Optional[Session] = None) -> "ToolRouter":
        """创建并注册基础工具的 ToolRouter"""
        router = cls()
        from .tools.basic import register_basic_tools
        register_basic_tools(router, db)
        logger.info(f"ToolRouter created with {len(router._local_tools)} basic tools")
        return router
    
    @classmethod
    def create_with_all_tools(cls, db: Optional[Session] = None) -> "ToolRouter":
        """创建并注册所有工具的 ToolRouter（包括搜索工具）"""
        router = cls()
        from .tools.basic import register_basic_tools
        from .tools.search_tools import register_search_tools
        
        register_basic_tools(router, db)
        register_search_tools(router)
        
        logger.info(f"ToolRouter created with {len(router._local_tools)} tools (including search)")
        return router
    
    @classmethod
    def create_with_ext_tools(cls, db: Optional[Session] = None) -> "ToolRouter":
        """创建并注册所有工具的 ToolRouter（包括扩展工具库）"""
        router = cls()
        from .tools.basic import register_basic_tools
        from .tools.search_tools import register_search_tools
        from .tools.ext import register_all_ext_tools
        
        register_basic_tools(router, db)
        register_search_tools(router)
        register_all_ext_tools(router)
        
        logger.info(f"ToolRouter created with {len(router._local_tools)} tools (full)")
        return router
    
    @classmethod
    async def create_with_mcp(cls, db: Optional[Session] = None, use_mock: bool = False) -> "ToolRouter":
        """
        创建包含 MCP 工具的 ToolRouter
        
        Args:
            db: 数据库 session
            use_mock: 是否使用 Mock MCP（用于测试）
        """
        router = cls()
        from .tools.basic import register_basic_tools
        from .tools.search_tools import register_search_tools
        from .tools.ext import register_all_ext_tools
        
        register_basic_tools(router, db)
        register_search_tools(router)
        register_all_ext_tools(router)
        
        # 加载 MCP 工具
        if use_mock:
            await router.load_mock_mcp()
        else:
            await router.load_mcp_from_env()
        
        total = len(router._local_tools) + len(router._mcp_tools)
        logger.info(f"ToolRouter created with {total} tools ({len(router._mcp_tools)} MCP)")
        return router
    
    def register_tool(self, tool: AliceTool):
        """注册本地工具"""
        self._local_tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")
    
    def register_mcp_tool(self, tool: McpBackedTool):
        """注册 MCP 工具"""
        # 检查名称冲突
        if tool.name in self._local_tools:
            logger.warning(f"MCP tool '{tool.name}' conflicts with local tool, skipping")
            return
        self._mcp_tools[tool.name] = tool
        logger.debug(f"Registered MCP tool: {tool.name}")
    
    async def load_mcp_from_env(self):
        """从环境变量加载 MCP 配置并连接"""
        self._mcp_registry = McpRegistry.from_env()
        
        if not self._mcp_registry.list_endpoints():
            logger.debug("No MCP endpoints configured")
            return
        
        # 连接所有 MCP Server
        results = await self._mcp_registry.connect_all()
        
        # 注册工具
        for name, client in [(n, self._mcp_registry.get_client(n)) for n in self._mcp_registry.list_endpoints()]:
            if client and results.get(name):
                await self._register_mcp_tools_from_client(client)
    
    async def load_mock_mcp(self):
        """加载 Mock MCP（用于测试）"""
        mock_client = MockMcpClient("mock")
        await mock_client.connect()
        await self._register_mcp_tools_from_client(mock_client)
    
    async def _register_mcp_tools_from_client(self, client: McpClient):
        """从 MCP Client 注册工具"""
        tools = await client.list_tools()
        
        for tool_desc in tools:
            mcp_tool = McpBackedTool(
                client=client,
                tool_name=tool_desc["name"],
                tool_description=tool_desc["description"],
                tool_parameters=tool_desc["parameters"],
                server_name=client.server_name,
            )
            self.register_mcp_tool(mcp_tool)
    
    def list_tools(self) -> List[str]:
        """获取所有已注册的工具名称"""
        return list(self._local_tools.keys()) + list(self._mcp_tools.keys())
    
    def list_tool_schemas(
        self, 
        allowed_tools: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        获取可用工具的 schema 列表
        
        Args:
            allowed_tools: 允许使用的工具名称列表，None 表示全部
            
        Returns:
            OpenAI function calling 格式的工具列表
        """
        schemas = []
        
        for name, tool in self._local_tools.items():
            if allowed_tools is None or name in allowed_tools:
                schemas.append(tool.to_schema())
        
        # 合并 MCP 工具
        for name, tool in self._mcp_tools.items():
            if allowed_tools is None or name in allowed_tools:
                schemas.append(tool.to_schema())
        
        return schemas
    
    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        执行工具调用
        
        Args:
            tool_name: 工具名称
            args: 工具参数
            
        Returns:
            工具执行结果
        """
        logger.info(f"Executing tool: {tool_name} with args: {args}")
        
        try:
            if tool_name in self._local_tools:
                result = await self._local_tools[tool_name].run(args)
                logger.info(f"Tool {tool_name} completed successfully")
                return result
            
            if tool_name in self._mcp_tools:
                result = await self._mcp_tools[tool_name].run(args)
                logger.info(f"MCP Tool {tool_name} completed successfully")
                return result
            
            raise ValueError(f"Unknown tool: {tool_name}")
            
        except Exception as e:
            logger.error(f"Tool {tool_name} failed: {e}")
            raise
    
    async def execute_safe(self, tool_name: str, args: Dict[str, Any]) -> ToolResult:
        """
        安全执行工具调用（捕获异常）
        
        Returns:
            ToolResult 包含执行结果或错误信息
        """
        try:
            result = await self.execute(tool_name, args)
            return ToolResult(
                success=True,
                output=result,
                summary=str(result)[:500] if result else None,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e),
            )
