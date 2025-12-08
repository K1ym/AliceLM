"""
ModelRegistry - 模型选择中心

职责：根据 (tenant_id, task_type) 返回 ResolvedModel
替代老的 ConfigService.get_task_llm_config() 决策逻辑
"""

import os
from pathlib import Path
from typing import Dict, Optional, Any
import yaml

from packages.logging import get_logger
from .types import ModelProfile, ResolvedModel, ModelKind

logger = get_logger(__name__)


class ModelRegistry:
    """
    模型注册表（控制平面核心组件）
    
    行为：
    1. 从 config/models.yaml 加载 profile 目录
    2. 从 task_defaults 获取任务默认 profile
    3. 如果有 tenant/user 覆盖配置，优先使用覆盖
    4. 返回 ResolvedModel 包含 provider/model/api_key 等信息
    """
    
    def __init__(
        self,
        profiles: Dict[str, ModelProfile],
        task_defaults: Dict[str, str],
        config_service: Optional[Any] = None,  # 老世界的 ConfigService，用于读取用户覆盖
    ):
        self._profiles = profiles
        self._task_defaults = task_defaults
        self._config_service = config_service
        logger.info(f"ModelRegistry initialized with {len(profiles)} profiles")
    
    @classmethod
    def from_yaml(cls, yaml_path: str = "config/models.yaml", config_service: Optional[Any] = None) -> "ModelRegistry":
        """从 YAML 文件加载"""
        path = Path(yaml_path)
        if not path.exists():
            logger.warning(f"Models config not found: {yaml_path}, using empty config")
            return cls({}, {}, config_service)
        
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        profiles = {}
        for profile_id, profile_data in data.get("model_profiles", {}).items():
            profiles[profile_id] = ModelProfile(id=profile_id, **profile_data)
        
        task_defaults = data.get("task_defaults", {})
        
        return cls(profiles, task_defaults, config_service)
    
    def get_profile(self, profile_id: str) -> Optional[ModelProfile]:
        """获取指定 profile"""
        return self._profiles.get(profile_id)
    
    def list_profiles(self, kind: Optional[str] = None) -> Dict[str, ModelProfile]:
        """列出所有 profile（可按类型过滤）"""
        if kind is None:
            return self._profiles.copy()
        return {k: v for k, v in self._profiles.items() if v.kind == kind}
    
    async def resolve_for_task(
        self,
        task_type: str,
        tenant_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> ResolvedModel:
        """
        解析任务所需的模型
        
        优先级（高到低）：
        1. 用户/租户级别覆盖（从 ConfigService 读取）
        2. YAML task_defaults 映射
        3. 硬编码 fallback
        """
        # Step 1: 尝试从用户配置获取覆盖
        user_override = await self._get_user_override(user_id, task_type) if user_id else None
        
        if user_override:
            return user_override
        
        # Step 2: 从 task_defaults 获取默认 profile
        profile_id = self._task_defaults.get(task_type)
        
        if not profile_id:
            # 根据任务类型推断 kind 并选择默认
            kind = self._infer_kind_from_task(task_type)
            profile_id = self._get_default_for_kind(kind)
        
        if not profile_id or profile_id not in self._profiles:
            # 最终 fallback
            profile_id = "alice.chat.main"
            if profile_id not in self._profiles:
                raise ValueError(f"No model profile configured for task: {task_type}")
        
        profile = self._profiles[profile_id]
        
        # Step 3: 合并 API 配置（从环境变量或 ConfigService）
        base_url, api_key = await self._get_api_config(profile.provider, user_id)
        
        return ResolvedModel(
            profile_id=profile.id,
            provider=profile.provider,
            model=profile.model,
            kind=profile.kind,
            max_input_tokens=profile.max_input_tokens,
            max_output_tokens=profile.max_output_tokens,
            embedding_dim=profile.embedding_dim,
            base_url=base_url,
            api_key=api_key,
        )
    
    async def _get_user_override(self, user_id: int, task_type: str) -> Optional[ResolvedModel]:
        """从用户配置获取覆盖"""
        if not self._config_service:
            return None
        
        try:
            # 调用老的 ConfigService 获取用户配置
            task_config = self._config_service.get_task_llm_config(user_id, task_type)
            
            if task_config and task_config.get("model"):
                return ResolvedModel(
                    profile_id=f"user.{user_id}.{task_type}",
                    provider=task_config.get("provider", "openai"),
                    model=task_config["model"],
                    kind=self._infer_kind_from_task(task_type),
                    base_url=task_config.get("base_url"),
                    api_key=task_config.get("api_key"),
                )
        except Exception as e:
            logger.warning(f"Failed to get user override: {e}")
        
        return None
    
    async def _get_api_config(self, provider: str, user_id: Optional[int]) -> tuple[Optional[str], Optional[str]]:
        """获取 API 配置（base_url, api_key）"""
        # 优先从环境变量获取
        env_prefix = provider.upper()
        base_url = os.getenv(f"{env_prefix}_BASE_URL") or os.getenv("OPENAI_BASE_URL")
        api_key = os.getenv(f"{env_prefix}_API_KEY") or os.getenv("OPENAI_API_KEY")
        
        # 如果有用户配置，尝试覆盖
        if user_id and self._config_service:
            try:
                llm_config = self._config_service.get_config_dict(user_id, "llm")
                if llm_config:
                    base_url = llm_config.get("base_url") or base_url
                    api_key = llm_config.get("api_key") or api_key
            except Exception:
                pass
        
        return base_url, api_key
    
    def _infer_kind_from_task(self, task_type: str) -> str:
        """从任务类型推断模型 kind"""
        if task_type in ("embedding",):
            return ModelKind.EMBEDDING.value
        if task_type in ("asr",):
            return ModelKind.ASR.value
        return ModelKind.CHAT.value
    
    def _get_default_for_kind(self, kind: str) -> Optional[str]:
        """获取某个 kind 的默认 profile"""
        for profile_id, profile in self._profiles.items():
            if profile.kind == kind:
                return profile_id
        return None
