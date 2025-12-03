"""
ASR管理器
统一管理不同的ASR提供者
"""

from typing import Dict, Optional, Type

from packages.config import get_config
from packages.logging import get_logger

from .base import ASRProvider, TranscriptResult

logger = get_logger(__name__)


class ASRManager:
    """ASR管理器"""

    _providers: Dict[str, Type[ASRProvider]] = {}

    def __init__(self, default_provider: Optional[str] = None):
        """
        初始化ASR管理器
        
        Args:
            default_provider: 默认提供者名称
        """
        config = get_config()
        self.default_provider = default_provider or config.asr.provider
        self._instances: Dict[str, ASRProvider] = {}
        
        # 注册内置提供者
        self._register_builtin_providers()

    def _register_builtin_providers(self):
        """注册内置提供者"""
        from .whisper_local import WhisperLocalProvider
        from .faster_whisper import FasterWhisperProvider

        self.register("whisper_local", WhisperLocalProvider)
        self.register("faster_whisper", FasterWhisperProvider)

    @classmethod
    def register(cls, name: str, provider_class: Type[ASRProvider]):
        """注册ASR提供者"""
        cls._providers[name] = provider_class
        logger.debug("asr_provider_registered", name=name)

    def get_provider(self, name: Optional[str] = None) -> ASRProvider:
        """
        获取ASR提供者实例
        
        Args:
            name: 提供者名称（默认使用配置的默认提供者）
            
        Returns:
            ASR提供者实例
        """
        name = name or self.default_provider

        if name not in self._instances:
            if name not in self._providers:
                raise ValueError(f"未知的ASR提供者: {name}")

            config = get_config()
            provider_class = self._providers[name]

            # 根据配置创建实例
            if name == "whisper_local":
                self._instances[name] = provider_class(
                    model_size=config.asr.model_size,
                    device=config.asr.device,
                )
            elif name == "faster_whisper":
                self._instances[name] = provider_class(
                    model_size=config.asr.model_size,
                    device=config.asr.device,
                )
            else:
                self._instances[name] = provider_class()

            logger.info("asr_provider_created", name=name)

        return self._instances[name]

    def transcribe(
        self,
        audio_path: str,
        provider: Optional[str] = None,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> TranscriptResult:
        """
        执行转写
        
        Args:
            audio_path: 音频文件路径
            provider: 提供者名称（可选）
            language: 语言（可选）
            prompt: 提示词（可选）
            
        Returns:
            转写结果
        """
        asr = self.get_provider(provider)
        return asr.transcribe(audio_path, language=language, prompt=prompt)

    def list_providers(self) -> list:
        """列出可用的提供者"""
        available = []
        for name, provider_class in self._providers.items():
            try:
                instance = provider_class()
                if instance.is_available():
                    available.append(name)
            except Exception:
                pass
        return available
