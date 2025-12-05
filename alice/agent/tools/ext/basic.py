"""
基础工具集

包含：calculator, current_time, sleep, environment, journal
"""

import ast
import logging
import operator
import os
import time
from datetime import datetime
from datetime import timezone as tz
from typing import Dict, Any, Optional, Union

from alice.agent.tool_router import AliceTool

logger = logging.getLogger(__name__)


class CalculatorTool(AliceTool):
    """
    计算器工具
    
    支持基础算术运算和简单数学表达式
    """
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return "执行数学计算，支持加减乘除、幂运算、括号等基础运算"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，如 '2 + 3 * 4' 或 '(10 - 5) ** 2'",
                },
            },
            "required": ["expression"],
        }
    
    # 安全的操作符映射
    _SAFE_OPERATORS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }
    
    def _safe_eval(self, node: ast.AST) -> Union[int, float]:
        """安全地计算 AST 节点"""
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"不支持的常量类型: {type(node.value)}")
        
        if isinstance(node, ast.BinOp):
            left = self._safe_eval(node.left)
            right = self._safe_eval(node.right)
            op = self._SAFE_OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"不支持的操作符: {type(node.op).__name__}")
            return op(left, right)
        
        if isinstance(node, ast.UnaryOp):
            operand = self._safe_eval(node.operand)
            op = self._SAFE_OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"不支持的一元操作符: {type(node.op).__name__}")
            return op(operand)
        
        if isinstance(node, ast.Expression):
            return self._safe_eval(node.body)
        
        raise ValueError(f"不支持的表达式类型: {type(node).__name__}")
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        expression = args.get("expression", "")
        if not expression:
            return {"error": "expression 参数不能为空"}
        
        try:
            # 解析并安全计算
            tree = ast.parse(expression, mode='eval')
            result = self._safe_eval(tree)
            
            return {
                "expression": expression,
                "result": result,
                "formatted": f"{expression} = {result}",
            }
        except Exception as e:
            return {"error": f"计算失败: {str(e)}"}


class CurrentTimeTool(AliceTool):
    """
    当前时间工具
    
    返回 ISO 8601 格式的当前时间
    """
    
    @property
    def name(self) -> str:
        return "current_time"
    
    @property
    def description(self) -> str:
        return "获取当前时间，返回 ISO 8601 格式"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "时区，如 'UTC', 'Asia/Shanghai', 'US/Pacific'",
                    "default": "Asia/Shanghai",
                },
            },
        }
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        timezone_str = args.get("timezone", "Asia/Shanghai")
        
        try:
            if timezone_str.upper() == "UTC":
                timezone_obj = tz.utc
            else:
                from zoneinfo import ZoneInfo
                timezone_obj = ZoneInfo(timezone_str)
            
            now = datetime.now(timezone_obj)
            return {
                "iso": now.isoformat(),
                "formatted": now.strftime("%Y-%m-%d %H:%M:%S %Z"),
                "timezone": timezone_str,
            }
        except Exception as e:
            return {"error": f"获取时间失败: {str(e)}"}


class SleepTool(AliceTool):
    """
    休眠工具
    
    暂停执行指定秒数
    """
    
    MAX_SLEEP_SECONDS = 300  # 最大 5 分钟
    
    @property
    def name(self) -> str:
        return "sleep"
    
    @property
    def description(self) -> str:
        return f"暂停执行指定秒数（最大 {self.MAX_SLEEP_SECONDS} 秒）"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "seconds": {
                    "type": "number",
                    "description": "休眠秒数",
                    "minimum": 0.1,
                    "maximum": self.MAX_SLEEP_SECONDS,
                },
            },
            "required": ["seconds"],
        }
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        seconds = args.get("seconds", 0)
        
        if not isinstance(seconds, (int, float)):
            return {"error": "seconds 必须是数字"}
        
        if seconds <= 0:
            return {"error": "seconds 必须大于 0"}
        
        if seconds > self.MAX_SLEEP_SECONDS:
            return {"error": f"seconds 不能超过 {self.MAX_SLEEP_SECONDS}"}
        
        start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        time.sleep(seconds)
        end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return {
            "started_at": start_time,
            "ended_at": end_time,
            "slept_seconds": seconds,
        }


class EnvironmentTool(AliceTool):
    """
    环境变量工具
    
    查看环境变量（只读，出于安全考虑不允许修改）
    """
    
    # 安全的环境变量前缀白名单
    SAFE_PREFIXES = ["ALICE_", "DEFAULT_", "TZ", "LANG", "LC_"]
    
    @property
    def name(self) -> str:
        return "environment"
    
    @property
    def description(self) -> str:
        return "查看系统环境变量（仅限安全变量）"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "get"],
                    "description": "操作类型：list 列出所有，get 获取单个",
                    "default": "list",
                },
                "name": {
                    "type": "string",
                    "description": "变量名（action=get 时必填）",
                },
            },
        }
    
    def _is_safe_var(self, name: str) -> bool:
        """检查变量是否在安全白名单中"""
        return any(name.startswith(prefix) for prefix in self.SAFE_PREFIXES)
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        action = args.get("action", "list")
        
        if action == "list":
            safe_vars = {
                k: v for k, v in os.environ.items()
                if self._is_safe_var(k)
            }
            return {"variables": safe_vars, "count": len(safe_vars)}
        
        elif action == "get":
            name = args.get("name", "")
            if not name:
                return {"error": "name 参数不能为空"}
            
            if not self._is_safe_var(name):
                return {"error": f"不允许访问变量 {name}"}
            
            value = os.environ.get(name)
            if value is None:
                return {"error": f"变量 {name} 不存在"}
            
            return {"name": name, "value": value}
        
        return {"error": f"未知操作: {action}"}


class JournalTool(AliceTool):
    """
    日志/日记工具
    
    记录 Agent 执行过程中的关键信息（内存级别）
    """
    
    _entries = []  # 类级别的日志存储
    
    @property
    def name(self) -> str:
        return "journal"
    
    @property
    def description(self) -> str:
        return "记录执行日志或读取历史记录"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["write", "read", "clear"],
                    "description": "操作类型",
                    "default": "write",
                },
                "content": {
                    "type": "string",
                    "description": "日志内容（action=write 时必填）",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回条数限制（action=read 时可选）",
                    "default": 10,
                },
            },
        }
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        action = args.get("action", "write")
        
        if action == "write":
            content = args.get("content", "")
            if not content:
                return {"error": "content 参数不能为空"}
            
            entry = {
                "timestamp": datetime.now().isoformat(),
                "content": content,
            }
            JournalTool._entries.append(entry)
            return {"success": True, "entry": entry}
        
        elif action == "read":
            limit = args.get("limit", 10)
            entries = JournalTool._entries[-limit:]
            return {"entries": entries, "total": len(JournalTool._entries)}
        
        elif action == "clear":
            count = len(JournalTool._entries)
            JournalTool._entries.clear()
            return {"success": True, "cleared": count}
        
        return {"error": f"未知操作: {action}"}


def get_basic_ext_tools():
    """获取所有基础扩展工具实例"""
    return [
        CalculatorTool(),
        CurrentTimeTool(),
        SleepTool(),
        EnvironmentTool(),
        JournalTool(),
    ]


def register_basic_ext_tools(router):
    """注册基础扩展工具到 ToolRouter"""
    for tool in get_basic_ext_tools():
        router.register_tool(tool)
