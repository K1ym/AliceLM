"""
PromptStore - Prompt 获取中心

职责：根据 (tenant_id, key) 返回 prompt 文本
替代老的 DEFAULT_PROMPTS 常量和散落的 prompt 硬编码
"""

from pathlib import Path
from typing import Dict, Optional, Any
import yaml

from packages.logging import get_logger

logger = get_logger(__name__)


class PromptStore:
    """
    Prompt 存储（控制平面核心组件）
    
    行为：
    1. 从 config/prompts.yaml 加载默认 prompt
    2. 如果有 tenant/user 覆盖，优先使用覆盖
    3. 支持 prompt 模板变量替换
    """
    
    def __init__(
        self,
        prompts: Dict[str, str],
        config_service: Optional[Any] = None,
    ):
        self._prompts = prompts
        self._config_service = config_service
        logger.info(f"PromptStore initialized with {len(prompts)} prompts")
    
    @classmethod
    def from_yaml(cls, yaml_path: str = "config/prompts.yaml", config_service: Optional[Any] = None) -> "PromptStore":
        """从 YAML 文件加载"""
        path = Path(yaml_path)
        if not path.exists():
            logger.warning(f"Prompts config not found: {yaml_path}, using empty config")
            return cls({}, config_service)
        
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        prompts = data.get("prompts", {})
        return cls(prompts, config_service)
    
    def list_keys(self) -> list[str]:
        """列出所有 prompt key"""
        return list(self._prompts.keys())
    
    def get_default(self, key: str) -> Optional[str]:
        """获取默认 prompt（不考虑用户覆盖）"""
        return self._prompts.get(key)
    
    async def get(
        self,
        key: str,
        tenant_id: Optional[int] = None,
        user_id: Optional[int] = None,
        **template_vars,
    ) -> str:
        """
        获取 prompt
        
        优先级（高到低）：
        1. 用户级别覆盖（从 ConfigService 读取）
        2. 租户级别覆盖
        3. YAML 默认值
        4. 空字符串（如果都没有）
        
        支持老 key 映射：
        - "chat" -> "alice.task.chat"
        - "summary" -> "alice.task.summary"
        - 等等
        """
        # 处理老 key 映射
        resolved_key = self._map_legacy_key(key)
        
        prompt = None
        
        # Step 1: 尝试从用户配置获取覆盖
        if user_id and self._config_service:
            prompt = await self._get_user_prompt(user_id, resolved_key)
        
        # Step 2: 回退到 YAML 默认值
        if not prompt:
            prompt = self._prompts.get(resolved_key, "")
        
        # Step 3: 模板变量替换
        if template_vars and prompt:
            try:
                prompt = prompt.format(**template_vars)
            except KeyError:
                # 如果模板变量不完整，返回原始 prompt
                pass
        
        return prompt
    
    async def _get_user_prompt(self, user_id: int, key: str) -> Optional[str]:
        """从用户配置获取覆盖"""
        if not self._config_service:
            return None
        
        try:
            # 调用老的 ConfigService 获取用户自定义 prompt
            custom_prompts = self._config_service.get_config_dict(user_id, "custom_prompts")
            
            if custom_prompts and key in custom_prompts:
                return custom_prompts[key]
            
            # 兼容老的 key 映射（如 "chat" -> "alice.system.base"）
            old_key = self._map_old_key(key)
            if old_key and old_key in custom_prompts:
                return custom_prompts[old_key]
                
        except Exception as e:
            logger.warning(f"Failed to get user prompt: {e}")
        
        return None
    
    def _map_old_key(self, new_key: str) -> Optional[str]:
        """新 key 到老 key 的映射（兼容用户覆盖时查老 key）"""
        mapping = {
            "alice.system.base": "chat",
            "alice.task.chat": "chat",
            "alice.task.summary": "summary",
            "alice.task.knowledge": "knowledge",
            "alice.task.mindmap": "mindmap",
            "alice.task.tagger": "tagger",
            "alice.task.context_compress": "context_compress",
        }
        return mapping.get(new_key)
    
    def _map_legacy_key(self, legacy_key: str) -> str:
        """
        老 key 到新 key 的映射（让业务代码可以用老 key）
        
        例如：PromptStore.get("chat") -> 返回 alice.task.chat 的内容
        """
        legacy_mapping = {
            "chat": "alice.task.chat",
            "summary": "alice.task.summary",
            "knowledge": "alice.task.knowledge",
            "mindmap": "alice.task.mindmap",
            "tagger": "alice.task.tagger",
            "context_compress": "alice.task.context_compress",
            # 额外的便捷映射
            "system": "alice.system.base",
            "research": "alice.system.research",
            "asr": "alice.task.asr",
            "summary_quick": "alice.task.summary_quick",
            "tagger_concepts": "alice.task.tagger_concepts",
        }
        return legacy_mapping.get(legacy_key, legacy_key)  # 如果不在映射中，返回原 key
    
    def set_default(self, key: str, prompt: str):
        """设置默认 prompt（运行时修改）"""
        self._prompts[key] = prompt
    
    def get_sync(
        self,
        key: str,
        tenant_id: Optional[int] = None,
        user_id: Optional[int] = None,
        **template_vars,
    ) -> str:
        """
        同步版本：获取 prompt（用于无法 async 的场景）
        
        注意：此版本不会查用户覆盖，只返回 YAML 默认值
        """
        # 处理老 key 映射
        resolved_key = self._map_legacy_key(key)
        
        prompt = self._prompts.get(resolved_key, "")
        
        # 模板变量替换
        if template_vars and prompt:
            try:
                prompt = prompt.format(**template_vars)
            except KeyError:
                pass
        
        return prompt
