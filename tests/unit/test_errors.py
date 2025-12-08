"""
alice.errors 单元测试
"""

import pytest
from alice.errors import (
    AliceError,
    ConfigError,
    NetworkError,
    LLMError,
    LLMConnectionError,
    LLMResponseError,
    RateLimitError,
    ToolExecutionError,
    RAGError,
    is_retryable,
)


class TestErrorHierarchy:
    """测试错误类层级"""
    
    def test_all_errors_inherit_from_alice_error(self):
        """所有错误都应继承自 AliceError"""
        assert issubclass(ConfigError, AliceError)
        assert issubclass(NetworkError, AliceError)
        assert issubclass(LLMError, AliceError)
        assert issubclass(RAGError, AliceError)
    
    def test_llm_errors_inherit_from_llm_error(self):
        """LLM 相关错误继承自 LLMError"""
        assert issubclass(LLMConnectionError, LLMError)
        assert issubclass(LLMResponseError, LLMError)
    
    def test_llm_connection_error_is_network_error(self):
        """LLMConnectionError 也是 NetworkError"""
        assert issubclass(LLMConnectionError, NetworkError)


class TestRetryable:
    """测试可重试判断"""
    
    def test_network_error_is_retryable(self):
        """NetworkError 可重试"""
        error = NetworkError("connection failed")
        assert is_retryable(error) is True
    
    def test_config_error_not_retryable(self):
        """ConfigError 不可重试"""
        error = ConfigError("invalid config")
        assert is_retryable(error) is False
    
    def test_llm_connection_error_is_retryable(self):
        """LLMConnectionError 可重试"""
        error = LLMConnectionError("timeout")
        assert is_retryable(error) is True
    
    def test_llm_response_error_not_retryable(self):
        """LLMResponseError 不可重试"""
        error = LLMResponseError("parse failed")
        assert is_retryable(error) is False
    
    def test_rate_limit_error_is_retryable(self):
        """RateLimitError 可重试"""
        error = RateLimitError("too many requests", retry_after=5.0)
        assert is_retryable(error) is True
        assert error.retry_after == 5.0


class TestErrorMessages:
    """测试错误消息"""
    
    def test_alice_error_with_details(self):
        """AliceError 应正确显示详情"""
        error = AliceError("something failed", details={"key": "value"})
        assert "something failed" in str(error)
        assert error.details == {"key": "value"}
    
    def test_tool_execution_error(self):
        """ToolExecutionError 应包含工具名"""
        original = ValueError("invalid input")
        error = ToolExecutionError("search", "failed to search", original)
        assert "search" in str(error)
        assert error.tool_name == "search"
        assert error.original_error == original
