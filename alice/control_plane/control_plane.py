"""
AliceControlPlane - 控制平面总入口

职责：组合 ModelRegistry/PromptStore/ToolRegistry/ServiceFactory
提供统一的配置和服务访问入口
"""

from pathlib import Path
from typing import Optional, Any, List

from packages.logging import get_logger

from .types import ModelProfile, ResolvedModel, ToolConfig
from .model_registry import ModelRegistry
from .prompt_store import PromptStore
from .tool_registry import ToolRegistry
from .service_factory import ServiceFactory

logger = get_logger(__name__)


# 全局单例
_control_plane: Optional["AliceControlPlane"] = None


class AliceControlPlane:
    """
    Alice 控制平面（核心配置中心）
    
    这是新世界的统一入口：
    - 模型选择走 self.models
    - Prompt 获取走 self.prompts
    - 工具创建走 self.tools
    - Service 创建走 self.services
    
    老世界的 ConfigService/ModelTaskConfig/prompts.py 只作为数据源，
    决策逻辑全部在这里。
    """
    
    def __init__(
        self,
        models: ModelRegistry,
        prompts: PromptStore,
        tools: ToolRegistry,
        services: ServiceFactory,
        config_service: Optional[Any] = None,
    ):
        self.models = models
        self.prompts = prompts
        self.tools = tools
        self.services = services
        self._config_service = config_service
        logger.info("AliceControlPlane initialized")
    
    @classmethod
    def from_config(
        cls,
        config_dir: str = "config",
        config_service: Optional[Any] = None,
    ) -> "AliceControlPlane":
        """
        从配置目录加载控制平面
        
        Args:
            config_dir: 配置目录路径
            config_service: 老世界的 ConfigService（用于读取用户覆盖）
        """
        config_path = Path(config_dir)
        
        models = ModelRegistry.from_yaml(
            str(config_path / "models.yaml"),
            config_service,
        )
        prompts = PromptStore.from_yaml(
            str(config_path / "prompts.yaml"),
            config_service,
        )
        tools = ToolRegistry.from_yaml(
            str(config_path / "tools.yaml"),
        )
        services = ServiceFactory.from_yaml(
            str(config_path / "services.yaml"),
        )
        
        return cls(models, prompts, tools, services, config_service)
    
    # ========== 便捷方法 ==========
    
    async def resolve_model(
        self,
        task_type: str,
        tenant_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> ResolvedModel:
        """解析任务所需的模型"""
        return await self.models.resolve_for_task(task_type, tenant_id, user_id)
    
    async def get_prompt(
        self,
        key: str,
        tenant_id: Optional[int] = None,
        user_id: Optional[int] = None,
        **template_vars,
    ) -> str:
        """获取 prompt（异步版本，支持用户覆盖）"""
        return await self.prompts.get(key, tenant_id, user_id, **template_vars)
    
    def get_prompt_sync(
        self,
        key: str,
        tenant_id: Optional[int] = None,
        user_id: Optional[int] = None,
        **template_vars,
    ) -> str:
        """获取 prompt（同步版本，仅返回 YAML 默认值）"""
        return self.prompts.get_sync(key, tenant_id, user_id, **template_vars)
    
    def create_tools_for_scene(
        self,
        scene: str,
        tenant_id: Optional[int] = None,
        allowed_tools: Optional[List[str]] = None,
        db: Optional[Any] = None,
    ) -> List[Any]:
        """创建场景可用的工具"""
        return self.tools.create_tools(scene, tenant_id, allowed_tools, db)
    
    def get_service(self, service_name: str, tenant_id: Optional[int] = None) -> Any:
        """获取服务实例"""
        return self.services.get_or_create(service_name, tenant_id)
    
    async def create_llm_for_task(
        self,
        task_type: str,
        tenant_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Any:
        """
        为指定任务创建 LLM 实例
        
        统一的 LLM 创建入口，替代散落的 create_llm_from_config/LLMManager() 调用
        
        Args:
            task_type: 任务类型 (chat/summary/embedding/asr/...)
            tenant_id: 租户 ID
            user_id: 用户 ID
            
        Returns:
            LLMManager 实例
        """
        from services.ai.llm import LLMManager, create_llm_from_config
        
        resolved = await self.resolve_model(task_type, tenant_id, user_id)
        
        if resolved.base_url and resolved.api_key:
            return create_llm_from_config(
                base_url=resolved.base_url,
                api_key=resolved.api_key,
                model=resolved.model,
            )
        else:
            # 回退到默认 LLMManager
            return LLMManager()
    
    def create_llm_for_task_sync(
        self,
        task_type: str,
        tenant_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Any:
        """
        同步版本：为指定任务创建 LLM 实例
        
        用于无法使用 async 的场景
        """
        import asyncio
        
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self.create_llm_for_task(task_type, tenant_id, user_id)
            )
        finally:
            loop.close()
    
    # ========== 信息查询 ==========
    
    def list_model_profiles(self, kind: Optional[str] = None) -> dict:
        """列出所有模型 profile"""
        return {k: v.model_dump() for k, v in self.models.list_profiles(kind).items()}
    
    def list_prompt_keys(self) -> list:
        """列出所有 prompt key"""
        return self.prompts.list_keys()
    
    def list_tools_for_scene(self, scene: str) -> list:
        """列出场景可用的工具"""
        return self.tools.list_tools_for_scene(scene)
    
    def get_service_provider(self, service_name: str) -> Optional[str]:
        """获取服务当前使用的 provider"""
        return self.services.get_provider_name(service_name)


def get_control_plane(config_service: Optional[Any] = None) -> AliceControlPlane:
    """
    获取全局控制平面实例（单例）
    
    Args:
        config_service: 老世界的 ConfigService
    """
    global _control_plane
    
    if _control_plane is None:
        _control_plane = AliceControlPlane.from_config(
            config_dir="config",
            config_service=config_service,
        )
    
    return _control_plane


def reset_control_plane():
    """重置控制平面（用于测试）"""
    global _control_plane
    _control_plane = None
