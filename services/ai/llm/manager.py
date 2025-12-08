"""
LLM管理器
"""

from typing import Dict, Optional, Type

from packages.config import get_config
from packages.logging import get_logger

from .base import LLMProvider, LLMResponse, Message

logger = get_logger(__name__)


class LLMManager:
    """LLM管理器"""

    _providers: Dict[str, Type[LLMProvider]] = {}

    def __init__(
        self,
        default_provider: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        初始化LLM管理器
        
        Args:
            default_provider: 默认提供者名称
            api_key: API密钥（覆盖配置）
            base_url: API地址（覆盖配置）
            model: 模型名称（覆盖配置）
        """
        config = get_config()
        self.default_provider = default_provider or config.llm.provider
        self._instances: Dict[str, LLMProvider] = {}
        
        # 动态配置（优先级高于全局配置）
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        
        # 注册内置提供者
        self._register_builtin_providers()

    def _register_builtin_providers(self):
        """注册内置提供者"""
        from .openai_provider import OpenAIProvider
        from .anthropic_provider import AnthropicProvider

        self.register("openai", OpenAIProvider)
        self.register("anthropic", AnthropicProvider)

    @classmethod
    def register(cls, name: str, provider_class: Type[LLMProvider]):
        """注册LLM提供者"""
        cls._providers[name] = provider_class
        logger.debug("llm_provider_registered", name=name)

    def get_provider(self, name: Optional[str] = None) -> LLMProvider:
        """获取LLM提供者实例"""
        name = name or self.default_provider
        
        # 使用动态配置时，每次都创建新实例
        cache_key = f"{name}_{self._base_url}_{self._model}"

        if cache_key not in self._instances:
            if name not in self._providers:
                # 默认使用OpenAI兼容接口
                name = "openai"

            config = get_config()
            provider_class = self._providers[name]

            # 使用动态配置，回退到全局配置
            api_key = self._api_key or config.llm.api_key
            base_url = self._base_url or config.llm.base_url
            model = self._model or config.llm.model

            # 根据配置创建实例
            if name == "openai":
                self._instances[cache_key] = provider_class(
                    api_key=api_key,
                    model=model,
                    base_url=base_url,
                )
            elif name == "anthropic":
                self._instances[cache_key] = provider_class(
                    api_key=api_key,
                )
            else:
                self._instances[cache_key] = provider_class()

            logger.info("llm_provider_created", name=name, model=model, base_url=base_url)

        return self._instances[cache_key]

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        provider: Optional[str] = None,
        **kwargs,
    ) -> str:
        """简单补全"""
        llm = self.get_provider(provider)
        return llm.complete(prompt, system_prompt, **kwargs)

    def chat(
        self,
        messages: list,
        provider: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """同步聊天补全"""
        llm = self.get_provider(provider)
        return llm.chat(messages, **kwargs)
    
    async def chat_async(
        self,
        messages: list,
        provider: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """异步聊天补全"""
        llm = self.get_provider(provider)
        return await llm.chat_async(messages, **kwargs)

    def chat_stream(
        self,
        messages: list,
        provider: Optional[str] = None,
        **kwargs,
    ):
        """流式聊天补全"""
        llm = self.get_provider(provider)
        return llm.chat_stream(messages, **kwargs)


def create_llm_from_config(base_url: str, api_key: str, model: str) -> LLMManager:
    """
    根据配置创建LLM管理器
    
    Args:
        base_url: API地址
        api_key: API密钥
        model: 模型名称
    
    Returns:
        配置好的LLMManager实例
    """
    return LLMManager(
        default_provider="openai",
        api_key=api_key,
        base_url=base_url,
        model=model,
    )
