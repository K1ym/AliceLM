"""
ToolRegistry - 工具选择中心

职责：根据 (scene, tenant_id) 决定 Agent 可以使用哪些工具
替代老的 ToolRouter.create_with_xxx() 硬编码逻辑
"""

import importlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Type
import yaml

from packages.logging import get_logger
from .types import ToolConfig

logger = get_logger(__name__)


class ToolRegistry:
    """
    工具注册表（控制平面核心组件）
    
    行为：
    1. 从 config/tools.yaml 加载工具配置
    2. 根据 scene 过滤可用工具
    3. 根据 enabled/unsafe 状态过滤
    4. 动态实例化工具类
    """
    
    def __init__(
        self,
        tools: List[ToolConfig],
        scene_defaults: Dict[str, List[str]],
    ):
        self._tools = {t.name: t for t in tools}
        self._scene_defaults = scene_defaults
        self._tool_cache: Dict[str, Any] = {}  # 工具实例缓存
        logger.info(f"ToolRegistry initialized with {len(tools)} tools")
    
    @classmethod
    def from_yaml(cls, yaml_path: str = "config/tools.yaml") -> "ToolRegistry":
        """从 YAML 文件加载"""
        path = Path(yaml_path)
        if not path.exists():
            logger.warning(f"Tools config not found: {yaml_path}, using empty config")
            return cls([], {})
        
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        tools = []
        for tool_data in data.get("tools", []):
            tools.append(ToolConfig(**tool_data))
        
        scene_defaults = data.get("scene_defaults", {})
        
        return cls(tools, scene_defaults)
    
    def list_tools(self, enabled_only: bool = True) -> List[ToolConfig]:
        """列出所有工具"""
        if enabled_only:
            return [t for t in self._tools.values() if t.enabled]
        return list(self._tools.values())
    
    def list_tools_for_scene(self, scene: str) -> List[str]:
        """列出场景可用的工具名称"""
        # 从 scene_defaults 获取
        default_tools = self._scene_defaults.get(scene, [])
        
        # 过滤掉未启用的
        result = []
        for name in default_tools:
            tool = self._tools.get(name)
            if tool and tool.enabled:
                result.append(name)
        
        return result
    
    def get_tool_config(self, name: str) -> Optional[ToolConfig]:
        """获取工具配置"""
        return self._tools.get(name)
    
    def create_tools(
        self,
        scene: str,
        tenant_id: Optional[int] = None,
        allowed_tools: Optional[List[str]] = None,
        db: Optional[Any] = None,
        include_unsafe: bool = False,
    ) -> List[Any]:
        """
        创建场景可用的工具实例
        
        Args:
            scene: 当前场景
            tenant_id: 租户 ID
            allowed_tools: 白名单（Strategy 提供）
            db: 数据库 session
            include_unsafe: 是否包含危险工具
            
        Returns:
            AliceTool 实例列表
        """
        # Step 1: 获取场景默认工具
        scene_tools = self.list_tools_for_scene(scene)
        
        # Step 2: 如果有白名单，取交集
        if allowed_tools is not None:
            scene_tools = [t for t in scene_tools if t in allowed_tools]
        
        # Step 3: 实例化工具
        tools = []
        for name in scene_tools:
            tool_config = self._tools.get(name)
            if not tool_config:
                continue
            
            # 过滤危险工具
            if tool_config.unsafe and not include_unsafe:
                continue
            
            try:
                tool = self._instantiate_tool(tool_config, db)
                if tool:
                    tools.append(tool)
            except Exception as e:
                logger.warning(f"Failed to instantiate tool {name}: {e}")
        
        logger.info(f"Created {len(tools)} tools for scene={scene}")
        return tools
    
    def _instantiate_tool(self, config: ToolConfig, db: Optional[Any] = None) -> Optional[Any]:
        """实例化工具类"""
        # 检查缓存
        cache_key = config.name
        if cache_key in self._tool_cache:
            return self._tool_cache[cache_key]
        
        try:
            # 动态导入
            module_path, class_name = config.impl.rsplit(".", 1)
            module = importlib.import_module(module_path)
            tool_class = getattr(module, class_name)
            
            # 尝试多种实例化方式
            try:
                # 方式 1: 传 db
                tool = tool_class(db=db)
            except TypeError:
                try:
                    # 方式 2: 无参数
                    tool = tool_class()
                except TypeError:
                    # 方式 3: 可能是函数式工具
                    tool = tool_class
            
            self._tool_cache[cache_key] = tool
            return tool
            
        except (ImportError, AttributeError) as e:
            logger.warning(f"Cannot import tool {config.impl}: {e}")
            return None
    
    def enable_tool(self, name: str):
        """启用工具"""
        if name in self._tools:
            self._tools[name].enabled = True
    
    def disable_tool(self, name: str):
        """禁用工具"""
        if name in self._tools:
            self._tools[name].enabled = False
