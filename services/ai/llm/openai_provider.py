"""
OpenAI兼容 LLM Provider
支持所有OpenAI API格式的服务：
- OpenAI (GPT-4, GPT-3.5等)
- DeepSeek
- 硅基流动 (SiliconFlow)
- Ollama (本地部署)
- vLLM
- 其他OpenAI兼容API
"""

from typing import List, Optional

from packages.config import get_config
from packages.logging import get_logger

from .base import LLMProvider, LLMResponse, Message

logger = get_logger(__name__)


class OpenAIProvider(LLMProvider):
    """
    OpenAI兼容 LLM提供者
    
    支持任何OpenAI API格式的端点，通过base_url配置：
    - OpenAI: https://api.openai.com/v1
    - DeepSeek: https://api.deepseek.com/v1
    - 硅基流动: https://api.siliconflow.cn/v1
    - Ollama: http://localhost:11434/v1
    """

    name = "openai"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        """
        初始化OpenAI兼容Provider
        
        Args:
            api_key: API密钥（Ollama本地可为空）
            model: 模型名称（如 gpt-4o-mini, deepseek-chat, qwen2.5等）
            base_url: API端点URL（支持自定义端点）
        
        环境变量:
            ALICE_LLM__API_KEY: API密钥
            ALICE_LLM__MODEL: 模型名称
            ALICE_LLM__BASE_URL: 自定义端点
        """
        config = get_config()
        
        self.api_key = api_key or config.llm.api_key or "sk-placeholder"
        self.model = model or config.llm.model or "gpt-4o-mini"
        self.base_url = base_url or config.llm.base_url or "https://api.openai.com/v1"
        
        self._client = None
        
        logger.debug(
            "llm_provider_init",
            provider=self.name,
            model=self.model,
            base_url=self.base_url,
        )

    def _get_client(self):
        """延迟初始化客户端"""
        if self._client is None:
            from openai import OpenAI
            import httpx
            
            # 思考模型可能需要更长时间，设置较长超时
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=httpx.Timeout(300.0, connect=30.0),  # 5分钟超时
            )
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

        # 转换消息格式
        api_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        logger.info(
            "llm_request",
            provider=self.name,
            model=self.model,
            messages_count=len(messages),
        )

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            result = LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                finish_reason=response.choices[0].finish_reason,
            )

            logger.info(
                "llm_response",
                provider=self.name,
                model=self.model,
                tokens=result.usage.get("total_tokens", 0),
            )

            return result

        except Exception as e:
            logger.error("llm_error", provider=self.name, error=str(e))
            raise

    def chat_stream(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs,
    ):
        """
        流式聊天补全
        
        Yields:
            dict: 包含 type(content/thinking/done), content, reasoning 等字段
        """
        client = self._get_client()

        api_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        logger.info(
            "llm_stream_request",
            provider=self.name,
            model=self.model,
            messages_count=len(messages),
        )

        try:
            stream = client.chat.completions.create(
                model=self.model,
                messages=api_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )

            full_content = ""
            full_reasoning = ""
            
            for chunk in stream:
                if not chunk.choices:
                    continue
                    
                delta = chunk.choices[0].delta
                finish_reason = chunk.choices[0].finish_reason
                
                # 处理思维链（如果API支持）
                # OpenAI o1/o3 使用 reasoning_content
                # DeepSeek R1 使用 reasoning_content
                reasoning_content = getattr(delta, 'reasoning_content', None)
                if reasoning_content:
                    full_reasoning += reasoning_content
                    yield {
                        "type": "thinking",
                        "content": reasoning_content,
                    }
                
                # 处理正常内容
                if delta.content:
                    full_content += delta.content
                    yield {
                        "type": "content",
                        "content": delta.content,
                    }
                
                # 完成
                if finish_reason:
                    yield {
                        "type": "done",
                        "finish_reason": finish_reason,
                        "full_content": full_content,
                        "full_reasoning": full_reasoning,
                    }

            logger.info(
                "llm_stream_complete",
                provider=self.name,
                model=self.model,
                content_length=len(full_content),
                reasoning_length=len(full_reasoning),
            )

        except Exception as e:
            logger.error("llm_stream_error", provider=self.name, error=str(e))
            yield {
                "type": "error",
                "error": str(e),
            }

    def is_available(self) -> bool:
        """检查是否可用"""
        # 有api_key或使用本地端点(Ollama)
        is_local = "localhost" in self.base_url or "127.0.0.1" in self.base_url
        return bool(self.api_key) or is_local

    def list_models(self) -> List[str]:
        """
        获取可用模型列表
        
        Returns:
            模型ID列表
        """
        client = self._get_client()
        try:
            models = client.models.list()
            model_ids = sorted([m.id for m in models.data])
            logger.info("models_fetched", count=len(model_ids), base_url=self.base_url)
            return model_ids
        except Exception as e:
            logger.error("models_fetch_failed", error=str(e))
            return []

    def save_models(self, path: str = "data/models.json") -> str:
        """
        获取并保存模型列表到文件
        
        Args:
            path: 保存路径
            
        Returns:
            保存的文件路径
        """
        import json
        from pathlib import Path
        from datetime import datetime
        
        models = self.list_models()
        
        data = {
            "base_url": self.base_url,
            "fetched_at": datetime.now().isoformat(),
            "count": len(models),
            "models": models,
        }
        
        out_path = Path(path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info("models_saved", path=str(out_path), count=len(models))
        return str(out_path)
