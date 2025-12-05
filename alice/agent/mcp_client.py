"""
MCP Client - Model Context Protocol 客户端

实现 MCP 协议的客户端，用于连接外部 MCP Server 并调用其工具。

MCP 协议使用 JSON-RPC 2.0 进行通信：
- tools/list: 获取工具列表
- tools/call: 调用工具
"""

import json
import logging
import os
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, TypedDict

import httpx

logger = logging.getLogger(__name__)


# ============================================================
# 数据类型定义
# ============================================================

class McpToolDescription(TypedDict):
    """MCP 工具描述"""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema


class McpServerStatus(str, Enum):
    """MCP Server 连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


@dataclass
class McpEndpointConfig:
    """MCP 端点配置"""
    name: str                           # 端点名称（唯一标识）
    endpoint: str                       # URL，如 http://localhost:3000/mcp
    api_key: Optional[str] = None       # API Key（可选）
    timeout: float = 30.0               # 超时秒数
    enabled: bool = True                # 是否启用


@dataclass
class McpToolResult:
    """MCP 工具调用结果"""
    success: bool
    content: Any = None                 # 返回内容
    error: Optional[str] = None         # 错误信息
    is_error: bool = False              # MCP 返回的 isError 标志


# ============================================================
# JSON-RPC 2.0 协议
# ============================================================

def make_jsonrpc_request(method: str, params: Optional[Dict] = None, id: Optional[str] = None) -> Dict:
    """构造 JSON-RPC 2.0 请求"""
    request = {
        "jsonrpc": "2.0",
        "method": method,
        "id": id or str(uuid.uuid4()),
    }
    if params is not None:
        request["params"] = params
    return request


def parse_jsonrpc_response(response: Dict) -> tuple[Any, Optional[str]]:
    """
    解析 JSON-RPC 2.0 响应
    
    Returns:
        (result, error_message)
    """
    if "error" in response:
        error = response["error"]
        error_msg = f"[{error.get('code', 'unknown')}] {error.get('message', 'Unknown error')}"
        return None, error_msg
    
    return response.get("result"), None


# ============================================================
# MCP Client
# ============================================================

class McpClient:
    """
    MCP 客户端
    
    连接单个 MCP Server，支持：
    - 列出工具 (tools/list)
    - 调用工具 (tools/call)
    """
    
    def __init__(
        self,
        endpoint: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        server_name: Optional[str] = None,
    ):
        """
        Args:
            endpoint: MCP Server URL
            api_key: API Key（可选）
            timeout: 请求超时秒数
            server_name: 服务器名称（用于日志和标识）
        """
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.server_name = server_name or endpoint
        self.status = McpServerStatus.DISCONNECTED
        self._tools_cache: Optional[List[McpToolDescription]] = None
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers
    
    async def _send_request(self, method: str, params: Optional[Dict] = None) -> tuple[Any, Optional[str]]:
        """
        发送 JSON-RPC 请求
        
        Returns:
            (result, error_message)
        """
        request = make_jsonrpc_request(method, params)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.endpoint,
                    json=request,
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                return parse_jsonrpc_response(response.json())
                
        except httpx.TimeoutException:
            return None, f"Request timeout ({self.timeout}s)"
        except httpx.HTTPStatusError as e:
            return None, f"HTTP error: {e.response.status_code}"
        except Exception as e:
            return None, f"Request failed: {str(e)}"
    
    async def connect(self) -> bool:
        """
        连接到 MCP Server（通过获取工具列表验证连接）
        
        Returns:
            是否连接成功
        """
        self.status = McpServerStatus.CONNECTING
        logger.info(f"🔌 Connecting to MCP server: {self.server_name}")
        
        try:
            tools, error = await self._send_request("tools/list")
            
            if error:
                self.status = McpServerStatus.ERROR
                logger.error(f"❌ MCP connection failed: {error}")
                return False
            
            self._tools_cache = self._parse_tools(tools)
            self.status = McpServerStatus.CONNECTED
            logger.info(f"✅ MCP connected: {self.server_name} ({len(self._tools_cache)} tools)")
            return True
            
        except Exception as e:
            self.status = McpServerStatus.ERROR
            logger.error(f"❌ MCP connection error: {e}")
            return False
    
    def _parse_tools(self, raw_tools: Any) -> List[McpToolDescription]:
        """解析工具列表响应"""
        if not raw_tools:
            return []
        
        # MCP 协议返回 {"tools": [...]}
        tools_list = raw_tools.get("tools", []) if isinstance(raw_tools, dict) else raw_tools
        
        parsed = []
        for tool in tools_list:
            if isinstance(tool, dict):
                parsed.append(McpToolDescription(
                    name=tool.get("name", ""),
                    description=tool.get("description", ""),
                    parameters=tool.get("inputSchema", tool.get("parameters", {})),
                ))
        
        return parsed
    
    async def list_tools(self) -> List[McpToolDescription]:
        """
        获取 MCP Server 上的工具列表
        
        Returns:
            工具描述列表
        """
        # 使用缓存
        if self._tools_cache is not None:
            return self._tools_cache
        
        result, error = await self._send_request("tools/list")
        
        if error:
            logger.error(f"Failed to list MCP tools: {error}")
            return []
        
        self._tools_cache = self._parse_tools(result)
        return self._tools_cache
    
    async def call_tool(self, name: str, args: Dict[str, Any]) -> McpToolResult:
        """
        调用 MCP 工具
        
        Args:
            name: 工具名称
            args: 工具参数
            
        Returns:
            McpToolResult
        """
        logger.info(f"🔧 Calling MCP tool: {name} on {self.server_name}")
        
        result, error = await self._send_request("tools/call", {
            "name": name,
            "arguments": args,
        })
        
        if error:
            return McpToolResult(
                success=False,
                error=error,
                is_error=True,
            )
        
        # 解析 MCP 响应
        # MCP 工具返回格式：{"content": [...], "isError": bool}
        if isinstance(result, dict):
            content = result.get("content", result)
            is_error = result.get("isError", False)
            
            # 提取文本内容
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                        elif "text" in item:
                            text_parts.append(item["text"])
                content = "\n".join(text_parts) if text_parts else content
            
            if is_error:
                return McpToolResult(
                    success=False,
                    content=content,
                    error=str(content),
                    is_error=True,
                )
            
            return McpToolResult(
                success=True,
                content=content,
            )
        
        return McpToolResult(
            success=True,
            content=result,
        )
    
    def invalidate_cache(self):
        """清除工具缓存"""
        self._tools_cache = None
    
    def disconnect(self):
        """断开连接"""
        self.status = McpServerStatus.DISCONNECTED
        self._tools_cache = None
        logger.info(f"🔌 Disconnected from MCP server: {self.server_name}")


# ============================================================
# MCP Registry - 管理多个 MCP 端点
# ============================================================

class McpRegistry:
    """
    MCP 注册表
    
    管理多个 MCP Server 连接
    """
    
    def __init__(self, configs: Optional[List[McpEndpointConfig]] = None):
        """
        Args:
            configs: MCP 端点配置列表
        """
        self._clients: Dict[str, McpClient] = {}
        self._configs: Dict[str, McpEndpointConfig] = {}
        
        if configs:
            for config in configs:
                self.add_endpoint(config)
    
    @classmethod
    def from_env(cls) -> "McpRegistry":
        """
        从环境变量创建 McpRegistry
        
        环境变量格式：
        ALICE_MCP__ENDPOINTS=name1:http://host1:port,name2:http://host2:port
        ALICE_MCP__API_KEY_name1=key1
        """
        registry = cls()
        
        endpoints_str = os.environ.get("ALICE_MCP__ENDPOINTS", "")
        if not endpoints_str:
            return registry
        
        for endpoint_def in endpoints_str.split(","):
            endpoint_def = endpoint_def.strip()
            if not endpoint_def:
                continue
            
            if ":" in endpoint_def:
                # 格式：name:url
                parts = endpoint_def.split(":", 1)
                if len(parts) == 2 and parts[1].startswith("http"):
                    name = parts[0]
                    url = parts[1]
                else:
                    # 格式可能是 name:http://...
                    name, url = endpoint_def.split(":", 1)
                    if url.startswith("//"):
                        url = "http:" + url
            else:
                name = endpoint_def
                url = endpoint_def
            
            api_key = os.environ.get(f"ALICE_MCP__API_KEY_{name}")
            
            registry.add_endpoint(McpEndpointConfig(
                name=name,
                endpoint=url,
                api_key=api_key,
            ))
        
        return registry
    
    def add_endpoint(self, config: McpEndpointConfig):
        """添加 MCP 端点"""
        if not config.enabled:
            return
        
        self._configs[config.name] = config
        self._clients[config.name] = McpClient(
            endpoint=config.endpoint,
            api_key=config.api_key,
            timeout=config.timeout,
            server_name=config.name,
        )
        logger.debug(f"Added MCP endpoint: {config.name} -> {config.endpoint}")
    
    def get_client(self, name: str) -> Optional[McpClient]:
        """获取指定名称的客户端"""
        return self._clients.get(name)
    
    def list_endpoints(self) -> List[str]:
        """列出所有端点名称"""
        return list(self._clients.keys())
    
    async def connect_all(self) -> Dict[str, bool]:
        """
        连接所有 MCP Server
        
        Returns:
            {endpoint_name: success}
        """
        results = {}
        for name, client in self._clients.items():
            results[name] = await client.connect()
        return results
    
    async def list_all_tools(self) -> Dict[str, List[McpToolDescription]]:
        """
        获取所有 MCP Server 的工具列表
        
        Returns:
            {endpoint_name: [tools]}
        """
        all_tools = {}
        for name, client in self._clients.items():
            if client.status == McpServerStatus.CONNECTED:
                all_tools[name] = await client.list_tools()
        return all_tools
    
    def disconnect_all(self):
        """断开所有连接"""
        for client in self._clients.values():
            client.disconnect()


# ============================================================
# Mock MCP Server（用于测试）
# ============================================================

class MockMcpClient(McpClient):
    """
    Mock MCP 客户端（用于测试）
    
    不发送实际 HTTP 请求，返回模拟数据
    """
    
    def __init__(self, server_name: str = "mock"):
        super().__init__(
            endpoint="http://mock.local",
            server_name=server_name,
        )
        self._mock_tools = [
            McpToolDescription(
                name="mock_echo",
                description="Echo the input message",
                parameters={
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "description": "Message to echo"},
                    },
                    "required": ["message"],
                },
            ),
            McpToolDescription(
                name="mock_add",
                description="Add two numbers",
                parameters={
                    "type": "object",
                    "properties": {
                        "a": {"type": "number", "description": "First number"},
                        "b": {"type": "number", "description": "Second number"},
                    },
                    "required": ["a", "b"],
                },
            ),
        ]
    
    async def connect(self) -> bool:
        self.status = McpServerStatus.CONNECTED
        self._tools_cache = self._mock_tools
        logger.info(f"✅ Mock MCP connected: {self.server_name}")
        return True
    
    async def list_tools(self) -> List[McpToolDescription]:
        return self._mock_tools
    
    async def call_tool(self, name: str, args: Dict[str, Any]) -> McpToolResult:
        logger.info(f"🔧 Mock MCP tool call: {name}({args})")
        
        if name == "mock_echo":
            message = args.get("message", "")
            return McpToolResult(
                success=True,
                content=f"Echo: {message}",
            )
        
        elif name == "mock_add":
            a = args.get("a", 0)
            b = args.get("b", 0)
            return McpToolResult(
                success=True,
                content={"result": a + b},
            )
        
        return McpToolResult(
            success=False,
            error=f"Unknown mock tool: {name}",
            is_error=True,
        )
