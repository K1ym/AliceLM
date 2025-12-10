"""
Anthropic Claude LLM Provider
"""

from typing import List, Optional

from packages.config import get_config
from packages.logging import get_logger
from alice.errors import AliceError, LLMError, LLMConnectionError, NetworkError

from .base import LLMProvider, LLMResponse, Message

logger = get_logger(__name__)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude LLM提供者"""

    name = "anthropic"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-haiku-20240307",
    ):
        """
        初始化Anthropic Provider
        
        Args:
            api_key: API密钥
            model: 模型名称
        """
        config = get_config()
        
        self.api_key = api_key or config.llm.api_key
        self.model = model
        
        self._client = None

    def _get_client(self):
        """延迟初始化客户端"""
        if self._client is None:
            from anthropic import Anthropic
            
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def chat(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ) -> LLMResponse:
        """聊天补全"""
        client = self._get_client()

        # 分离system消息
        system_content = None
        api_messages = []
        
        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            else:
                api_messages.append({
                    "role": msg.role,
                    "content": msg.content,
                })

        logger.info(
            "llm_request",
            provider=self.name,
            model=self.model,
            messages_count=len(messages),
        )

        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=max_tokens or 4096,
                system=system_content,
                messages=api_messages,
                temperature=temperature,
                **kwargs,
            )

            result = LLMResponse(
                content=response.content[0].text,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                },
                finish_reason=response.stop_reason,
            )

            logger.info(
                "llm_response",
                provider=self.name,
                model=self.model,
                tokens=result.usage.get("total_tokens", 0),
            )

            return result

        except (LLMError, LLMConnectionError, NetworkError):
            logger.exception("llm_error", provider=self.name)
            raise
        except Exception as e:
            logger.exception("llm_error_unexpected", provider=self.name)
            raise LLMError(str(e)) from e

    def is_available(self) -> bool:
        """检查是否可用"""
        return bool(self.api_key)
