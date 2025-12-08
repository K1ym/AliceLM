"""
services.ai.llm 单元测试
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from services.ai.llm import LLMManager, Message, LLMResponse


class TestLLMManager:
    """测试 LLMManager"""
    
    def test_init_with_defaults(self):
        """默认初始化"""
        manager = LLMManager()
        assert manager.default_provider is not None
    
    def test_init_with_custom_config(self):
        """自定义配置初始化"""
        manager = LLMManager(
            default_provider="openai",
            api_key="test-key",
            base_url="http://localhost:8000",
            model="gpt-4",
        )
        assert manager._api_key == "test-key"
        assert manager._base_url == "http://localhost:8000"
        assert manager._model == "gpt-4"
    
    def test_register_provider(self):
        """注册自定义 provider"""
        class MockProvider:
            name = "mock"
        
        LLMManager.register("mock", MockProvider)
        assert "mock" in LLMManager._providers
    
    def test_chat_returns_llm_response(self):
        """chat 返回 LLMResponse"""
        manager = LLMManager()
        
        # Mock provider
        mock_provider = MagicMock()
        mock_provider.chat.return_value = LLMResponse(
            content="Hello!",
            model="gpt-4",
            usage={"total_tokens": 10},
            finish_reason="stop",
        )
        manager._instances["test"] = mock_provider
        manager.default_provider = "test"
        
        messages = [Message(role="user", content="Hi")]
        with patch.object(manager, 'get_provider', return_value=mock_provider):
            response = manager.chat(messages)
        
        assert response.content == "Hello!"
        assert response.model == "gpt-4"
    
    def test_has_chat_async_method(self):
        """应有 chat_async 方法"""
        manager = LLMManager()
        assert hasattr(manager, 'chat_async')
        assert callable(manager.chat_async)


class TestMessage:
    """测试 Message"""
    
    def test_create_user_message(self):
        """创建用户消息"""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
    
    def test_create_system_message(self):
        """创建系统消息"""
        msg = Message(role="system", content="You are a helpful assistant")
        assert msg.role == "system"


class TestLLMResponse:
    """测试 LLMResponse"""
    
    def test_response_fields(self):
        """响应字段"""
        response = LLMResponse(
            content="Answer",
            model="gpt-4",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            finish_reason="stop",
        )
        assert response.content == "Answer"
        assert response.usage["total_tokens"] == 30
        assert response.finish_reason == "stop"
