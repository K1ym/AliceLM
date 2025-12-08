"""
Alice Control Plane - 控制平面模块

提供统一的配置和服务访问入口：
- ModelRegistry: 模型选择
- PromptStore: Prompt 获取
- ToolRegistry: 工具选择
- ServiceFactory: Service 创建
- AliceControlPlane: 总入口
"""

from .types import (
    ModelKind,
    ModelProfile,
    ResolvedModel,
    ToolConfig,
    ServiceConfig,
    ProviderConfig,
    ControlPlaneConfig,
)
from .model_registry import ModelRegistry
from .prompt_store import PromptStore
from .tool_registry import ToolRegistry
from .service_factory import ServiceFactory
from .control_plane import AliceControlPlane, get_control_plane, reset_control_plane


__all__ = [
    # Types
    "ModelKind",
    "ModelProfile",
    "ResolvedModel",
    "ToolConfig",
    "ServiceConfig",
    "ProviderConfig",
    "ControlPlaneConfig",
    # Components
    "ModelRegistry",
    "PromptStore",
    "ToolRegistry",
    "ServiceFactory",
    # Main entry
    "AliceControlPlane",
    "get_control_plane",
    "reset_control_plane",
]
