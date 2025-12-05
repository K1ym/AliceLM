"""
高危工具

⚠️ 警告：这些工具具有较高的安全风险
默认情况下 ToolRouter 不会加载这些工具

只能在以下情况使用：
1. Console/Admin 场景
2. 显式通过环境变量启用
3. 经过用户确认

包含：shell, python_repl, browser_control 等
"""

import logging
import os
import subprocess
from typing import Dict, Any

from alice.agent.tool_router import AliceTool

logger = logging.getLogger(__name__)


def is_unsafe_tools_enabled() -> bool:
    """检查高危工具是否已启用"""
    return os.environ.get("ALICE_UNSAFE_TOOLS_ENABLED", "false").lower() == "true"


class ShellTool(AliceTool):
    """
    Shell 命令执行工具
    
    ⚠️ 高危：可执行任意 shell 命令
    """
    
    TIMEOUT = 60  # 秒
    
    @property
    def name(self) -> str:
        return "shell"
    
    @property
    def description(self) -> str:
        return "执行 shell 命令（高危，需要显式启用）"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "要执行的 shell 命令",
                },
                "timeout": {
                    "type": "integer",
                    "description": "超时秒数",
                    "default": 60,
                },
            },
            "required": ["command"],
        }
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not is_unsafe_tools_enabled():
            return {
                "error": "Shell 工具已禁用。设置 ALICE_UNSAFE_TOOLS_ENABLED=true 以启用"
            }
        
        command = args.get("command", "")
        timeout = min(args.get("timeout", self.TIMEOUT), 300)
        
        if not command:
            return {"error": "command 参数不能为空"}
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            return {
                "command": command,
                "stdout": result.stdout[:10000],  # 限制输出
                "stderr": result.stderr[:2000],
                "return_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"error": f"命令超时 ({timeout}s)"}
        except Exception as e:
            return {"error": f"执行失败: {str(e)}"}


class PythonReplTool(AliceTool):
    """
    Python REPL 工具
    
    ⚠️ 高危：可执行任意 Python 代码
    """
    
    @property
    def name(self) -> str:
        return "python_repl"
    
    @property
    def description(self) -> str:
        return "执行 Python 代码（高危，需要显式启用）"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的 Python 代码",
                },
            },
            "required": ["code"],
        }
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not is_unsafe_tools_enabled():
            return {
                "error": "Python REPL 已禁用。设置 ALICE_UNSAFE_TOOLS_ENABLED=true 以启用"
            }
        
        code = args.get("code", "")
        if not code:
            return {"error": "code 参数不能为空"}
        
        # 创建受限的执行环境
        local_vars = {}
        global_vars = {
            "__builtins__": {
                "print": print,
                "len": len,
                "range": range,
                "str": str,
                "int": int,
                "float": float,
                "list": list,
                "dict": dict,
                "sum": sum,
                "min": min,
                "max": max,
                "sorted": sorted,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
            }
        }
        
        try:
            # 捕获输出
            import io
            import sys
            
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            
            try:
                exec(code, global_vars, local_vars)
                output = sys.stdout.getvalue()
            finally:
                sys.stdout = old_stdout
            
            return {
                "code": code,
                "output": output[:5000],
                "variables": {k: str(v)[:200] for k, v in local_vars.items()},
            }
        except Exception as e:
            return {"error": f"执行失败: {str(e)}"}


class BrowserControlTool(AliceTool):
    """
    浏览器控制工具
    
    ⚠️ 高危：控制浏览器执行操作
    """
    
    @property
    def name(self) -> str:
        return "browser_control"
    
    @property
    def description(self) -> str:
        return "控制浏览器（高危，未实现）"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["open", "click", "type", "screenshot"],
                    "description": "浏览器操作",
                },
                "url": {
                    "type": "string",
                    "description": "目标 URL",
                },
            },
            "required": ["action"],
        }
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"error": "浏览器控制功能尚未实现"}


class UseComputerTool(AliceTool):
    """
    计算机控制工具
    
    ⚠️ 高危：控制鼠标/键盘
    """
    
    @property
    def name(self) -> str:
        return "use_computer"
    
    @property
    def description(self) -> str:
        return "控制计算机（高危，未实现）"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "操作类型",
                },
            },
            "required": ["action"],
        }
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"error": "计算机控制功能尚未实现"}


class UseAwsTool(AliceTool):
    """
    AWS 操作工具
    
    ⚠️ 高危：操作 AWS 资源
    """
    
    @property
    def name(self) -> str:
        return "use_aws"
    
    @property
    def description(self) -> str:
        return "操作 AWS 资源（高危，未实现）"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "AWS 服务名",
                },
                "action": {
                    "type": "string",
                    "description": "操作",
                },
            },
            "required": ["service", "action"],
        }
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"error": "AWS 操作功能尚未实现"}


class SlackTool(AliceTool):
    """
    Slack 工具
    
    ⚠️ 需要 Slack Bot Token
    """
    
    @property
    def name(self) -> str:
        return "slack"
    
    @property
    def description(self) -> str:
        return "发送 Slack 消息（未实现）"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "频道 ID 或名称",
                },
                "message": {
                    "type": "string",
                    "description": "消息内容",
                },
            },
            "required": ["channel", "message"],
        }
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {"error": "Slack 功能尚未实现"}


def get_unsafe_tools():
    """
    获取高危工具列表
    
    ⚠️ 这些工具默认不应该被注册到 ToolRouter
    """
    return [
        ShellTool(),
        PythonReplTool(),
        BrowserControlTool(),
        UseComputerTool(),
        UseAwsTool(),
        SlackTool(),
    ]


def register_unsafe_tools(router):
    """
    注册高危工具
    
    ⚠️ 只在 Console/Admin 场景下使用
    """
    if not is_unsafe_tools_enabled():
        logger.warning("高危工具未启用，跳过注册")
        return
    
    logger.warning("⚠️ 正在注册高危工具，请确保在受信任环境中运行")
    for tool in get_unsafe_tools():
        router.register_tool(tool)
