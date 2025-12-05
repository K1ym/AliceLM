"""
文件操作工具

包含：file_read, file_write（受限于安全目录）
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from alice.agent.tool_router import AliceTool

logger = logging.getLogger(__name__)


# 安全目录配置（只允许在这些目录下操作）
SAFE_DIRECTORIES = [
    os.path.expanduser("~/alice_workspace"),
    "/tmp/alice",
]


def get_safe_directories():
    """获取安全目录列表"""
    custom = os.environ.get("ALICE_SAFE_DIRECTORIES", "")
    if custom:
        return [d.strip() for d in custom.split(",") if d.strip()]
    return SAFE_DIRECTORIES


def is_safe_path(path: str) -> bool:
    """检查路径是否在安全目录内"""
    abs_path = os.path.abspath(os.path.expanduser(path))
    for safe_dir in get_safe_directories():
        safe_abs = os.path.abspath(os.path.expanduser(safe_dir))
        if abs_path.startswith(safe_abs):
            return True
    return False


class FileReadTool(AliceTool):
    """
    文件读取工具
    
    只允许读取安全目录内的文件
    """
    
    MAX_FILE_SIZE = 1024 * 1024  # 1MB
    
    @property
    def name(self) -> str:
        return "file_read"
    
    @property
    def description(self) -> str:
        return "读取文件内容（仅限安全目录）"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径",
                },
                "encoding": {
                    "type": "string",
                    "description": "文件编码",
                    "default": "utf-8",
                },
                "max_lines": {
                    "type": "integer",
                    "description": "最大读取行数（0 表示全部）",
                    "default": 0,
                },
            },
            "required": ["path"],
        }
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        path = args.get("path", "")
        encoding = args.get("encoding", "utf-8")
        max_lines = args.get("max_lines", 0)
        
        if not path:
            return {"error": "path 参数不能为空"}
        
        # 安全检查
        if not is_safe_path(path):
            safe_dirs = get_safe_directories()
            return {
                "error": f"不允许访问该路径。安全目录: {safe_dirs}",
            }
        
        abs_path = os.path.abspath(os.path.expanduser(path))
        
        if not os.path.exists(abs_path):
            return {"error": f"文件不存在: {abs_path}"}
        
        if not os.path.isfile(abs_path):
            return {"error": f"不是文件: {abs_path}"}
        
        # 大小检查
        file_size = os.path.getsize(abs_path)
        if file_size > self.MAX_FILE_SIZE:
            return {
                "error": f"文件过大 ({file_size} bytes)，最大允许 {self.MAX_FILE_SIZE} bytes",
            }
        
        try:
            with open(abs_path, "r", encoding=encoding) as f:
                if max_lines > 0:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            break
                        lines.append(line)
                    content = "".join(lines)
                    truncated = True
                else:
                    content = f.read()
                    truncated = False
            
            return {
                "path": abs_path,
                "content": content,
                "size": file_size,
                "lines": content.count("\n") + 1,
                "truncated": truncated,
            }
        except Exception as e:
            return {"error": f"读取失败: {str(e)}"}


class FileWriteTool(AliceTool):
    """
    文件写入工具
    
    只允许写入安全目录内的文件
    默认禁用，需要通过环境变量启用
    """
    
    @property
    def name(self) -> str:
        return "file_write"
    
    @property
    def description(self) -> str:
        return "写入文件内容（仅限安全目录，默认禁用）"
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "文件路径",
                },
                "content": {
                    "type": "string",
                    "description": "文件内容",
                },
                "mode": {
                    "type": "string",
                    "enum": ["write", "append"],
                    "description": "写入模式",
                    "default": "write",
                },
                "encoding": {
                    "type": "string",
                    "description": "文件编码",
                    "default": "utf-8",
                },
            },
            "required": ["path", "content"],
        }
    
    def _is_enabled(self) -> bool:
        """检查写入功能是否启用"""
        return os.environ.get("ALICE_FILE_WRITE_ENABLED", "false").lower() == "true"
    
    async def run(self, args: Dict[str, Any]) -> Dict[str, Any]:
        # 功能开关检查
        if not self._is_enabled():
            return {
                "error": "文件写入功能已禁用。设置 ALICE_FILE_WRITE_ENABLED=true 以启用",
            }
        
        path = args.get("path", "")
        content = args.get("content", "")
        mode = args.get("mode", "write")
        encoding = args.get("encoding", "utf-8")
        
        if not path:
            return {"error": "path 参数不能为空"}
        
        # 安全检查
        if not is_safe_path(path):
            safe_dirs = get_safe_directories()
            return {
                "error": f"不允许访问该路径。安全目录: {safe_dirs}",
            }
        
        abs_path = os.path.abspath(os.path.expanduser(path))
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(abs_path), exist_ok=True)
            
            file_mode = "w" if mode == "write" else "a"
            with open(abs_path, file_mode, encoding=encoding) as f:
                f.write(content)
            
            return {
                "path": abs_path,
                "mode": mode,
                "bytes_written": len(content.encode(encoding)),
                "success": True,
            }
        except Exception as e:
            return {"error": f"写入失败: {str(e)}"}


def get_file_tools():
    """获取所有文件工具实例"""
    return [
        FileReadTool(),
        FileWriteTool(),
    ]


def register_file_tools(router):
    """注册文件工具到 ToolRouter"""
    for tool in get_file_tools():
        router.register_tool(tool)
