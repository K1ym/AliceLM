"""
工具权限与可见性控制

根据用户角色和场景控制工具的可见性和可用性
"""

import logging
from enum import Enum
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class UserRole(str, Enum):
    """用户角色"""
    ADMIN = "admin"
    NORMAL = "normal"
    GUEST = "guest"


class ToolCategory(str, Enum):
    """工具分类"""
    BASIC = "basic"           # 基础工具
    FILE = "file"             # 文件操作
    WEB = "web"               # Web/HTTP
    SEARCH = "search"         # 搜索
    MCP = "mcp"               # MCP 工具
    UNSAFE = "unsafe"         # 高危工具


# 工具到分类的映射
TOOL_CATEGORIES: Dict[str, ToolCategory] = {
    # 基础工具
    "echo": ToolCategory.BASIC,
    "current_time": ToolCategory.BASIC,
    "calculator": ToolCategory.BASIC,
    "sleep": ToolCategory.BASIC,
    "environment": ToolCategory.BASIC,
    "journal": ToolCategory.BASIC,
    
    # 文件工具
    "file_read": ToolCategory.FILE,
    "file_write": ToolCategory.FILE,
    
    # Web/HTTP 工具
    "http_request": ToolCategory.WEB,
    "tavily_search": ToolCategory.WEB,
    "tavily_extract": ToolCategory.WEB,
    "exa_search": ToolCategory.WEB,
    "exa_get_contents": ToolCategory.WEB,
    "rss": ToolCategory.WEB,
    "cron": ToolCategory.WEB,
    
    # 搜索工具
    "deep_web_research": ToolCategory.SEARCH,
    
    # 高危工具
    "shell": ToolCategory.UNSAFE,
    "python_repl": ToolCategory.UNSAFE,
    "browser_control": ToolCategory.UNSAFE,
    "use_computer": ToolCategory.UNSAFE,
    "use_aws": ToolCategory.UNSAFE,
    "slack": ToolCategory.UNSAFE,
}

# 场景允许的工具分类
SCENE_ALLOWED_CATEGORIES: Dict[str, Set[ToolCategory]] = {
    "chat": {ToolCategory.BASIC},
    "research": {ToolCategory.BASIC, ToolCategory.WEB, ToolCategory.SEARCH},
    "video": {ToolCategory.BASIC, ToolCategory.SEARCH},
    "library": {ToolCategory.BASIC, ToolCategory.SEARCH},
    "timeline": {ToolCategory.BASIC},
    "graph": {ToolCategory.BASIC},
    "console": {ToolCategory.BASIC, ToolCategory.FILE, ToolCategory.WEB, ToolCategory.SEARCH, ToolCategory.MCP},
}

# 角色允许的工具分类
ROLE_ALLOWED_CATEGORIES: Dict[UserRole, Set[ToolCategory]] = {
    UserRole.ADMIN: {ToolCategory.BASIC, ToolCategory.FILE, ToolCategory.WEB, ToolCategory.SEARCH, ToolCategory.MCP, ToolCategory.UNSAFE},
    UserRole.NORMAL: {ToolCategory.BASIC, ToolCategory.WEB, ToolCategory.SEARCH},
    UserRole.GUEST: {ToolCategory.BASIC},
}

# 默认禁止的工具（需要显式启用）
BLOCKED_BY_DEFAULT: Set[str] = {
    "shell",
    "python_repl",
    "browser_control",
    "use_computer",
    "use_aws",
    "slack",
    "file_write",
}


class ToolVisibilityPolicy:
    """
    工具可见性策略
    
    根据用户角色、场景和配置决定哪些工具可见
    """
    
    def __init__(
        self,
        user_role: str = "normal",
        scene: str = "chat",
        enable_unsafe: bool = False,
        extra_allowed: Optional[List[str]] = None,
        extra_blocked: Optional[List[str]] = None,
    ):
        """
        Args:
            user_role: 用户角色 (admin/normal/guest)
            scene: 场景 (chat/research/video/library/timeline/graph/console)
            enable_unsafe: 是否启用高危工具
            extra_allowed: 额外允许的工具列表
            extra_blocked: 额外禁止的工具列表
        """
        try:
            self.user_role = UserRole(user_role)
        except ValueError:
            self.user_role = UserRole.NORMAL
        
        self.scene = scene
        self.enable_unsafe = enable_unsafe
        self.extra_allowed = set(extra_allowed or [])
        self.extra_blocked = set(extra_blocked or [])
    
    def is_tool_allowed(self, tool_name: str) -> bool:
        """
        检查工具是否允许使用
        
        Args:
            tool_name: 工具名称
            
        Returns:
            是否允许
        """
        # 额外禁止的工具
        if tool_name in self.extra_blocked:
            return False
        
        # 额外允许的工具
        if tool_name in self.extra_allowed:
            return True
        
        # 默认禁止的工具需要显式启用
        if tool_name in BLOCKED_BY_DEFAULT:
            if not self.enable_unsafe:
                return False
            if self.user_role != UserRole.ADMIN:
                return False
        
        # 获取工具分类
        category = TOOL_CATEGORIES.get(tool_name)
        
        # 未知分类的工具（如 MCP 工具）
        if category is None:
            # MCP 工具默认归类为 MCP
            if tool_name.startswith("mock_") or "mcp" in tool_name.lower():
                category = ToolCategory.MCP
            else:
                category = ToolCategory.BASIC
        
        # 检查场景是否允许该分类
        scene_categories = SCENE_ALLOWED_CATEGORIES.get(self.scene, {ToolCategory.BASIC})
        if category not in scene_categories:
            # Console 场景下放宽限制
            if self.scene == "console":
                pass
            else:
                return False
        
        # 检查角色是否允许该分类
        role_categories = ROLE_ALLOWED_CATEGORIES.get(self.user_role, {ToolCategory.BASIC})
        if category not in role_categories:
            return False
        
        return True
    
    def filter_tools(self, tool_names: List[str]) -> List[str]:
        """
        过滤工具列表，只保留允许的工具
        
        Args:
            tool_names: 工具名称列表
            
        Returns:
            过滤后的工具列表
        """
        return [name for name in tool_names if self.is_tool_allowed(name)]
    
    @classmethod
    def from_extra_context(cls, extra_context: Optional[Dict] = None) -> "ToolVisibilityPolicy":
        """
        从 extra_context 创建策略
        
        Args:
            extra_context: AgentTask 的 extra_context
            
        Returns:
            ToolVisibilityPolicy
        """
        ctx = extra_context or {}
        
        return cls(
            user_role=ctx.get("user_role", "normal"),
            scene=ctx.get("scene", "chat"),
            enable_unsafe=ctx.get("enable_unsafe_tools", False),
            extra_allowed=ctx.get("extra_allowed_tools"),
            extra_blocked=ctx.get("extra_blocked_tools"),
        )


def get_allowed_tools_for_context(
    scene: str,
    user_role: str = "normal",
    enable_unsafe: bool = False,
) -> List[str]:
    """
    获取指定上下文允许的工具列表
    
    便捷函数
    """
    policy = ToolVisibilityPolicy(
        user_role=user_role,
        scene=scene,
        enable_unsafe=enable_unsafe,
    )
    
    # 返回所有已知工具中允许的
    return policy.filter_tools(list(TOOL_CATEGORIES.keys()))
