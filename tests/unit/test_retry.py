"""
packages.retry 单元测试
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from packages.retry import (
    with_retry,
    with_retry_sync,
    RetryExhaustedError,
    retry_with_timeout,
)


class TestWithRetry:
    """测试异步重试装饰器"""
    
    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """第一次成功不重试"""
        call_count = 0
        
        @with_retry(max_attempts=3)
        async def always_succeed():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await always_succeed()
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """失败后重试"""
        call_count = 0
        
        @with_retry(max_attempts=3, backoff_base=0.01)
        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("network error")
            return "success"
        
        result = await fail_then_succeed()
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_exhaust_retries(self):
        """重试耗尽抛出错误"""
        @with_retry(max_attempts=2, backoff_base=0.01)
        async def always_fail():
            raise ConnectionError("always fails")
        
        with pytest.raises(RetryExhaustedError) as exc_info:
            await always_fail()
        
        assert exc_info.value.attempts == 2
        assert isinstance(exc_info.value.last_error, ConnectionError)
    
    @pytest.mark.asyncio
    async def test_only_retry_specified_exceptions(self):
        """只重试指定的异常类型"""
        call_count = 0
        
        @with_retry(max_attempts=3, retryable_exceptions=(ConnectionError,))
        async def fail_with_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("not retryable")
        
        with pytest.raises(ValueError):
            await fail_with_value_error()
        
        # ValueError 不重试，只调用一次
        assert call_count == 1


class TestWithRetrySync:
    """测试同步重试装饰器"""
    
    def test_success_on_first_attempt(self):
        """第一次成功不重试"""
        call_count = 0
        
        @with_retry_sync(max_attempts=3)
        def always_succeed():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = always_succeed()
        assert result == "success"
        assert call_count == 1
    
    def test_exhaust_retries(self):
        """重试耗尽"""
        @with_retry_sync(max_attempts=2, backoff_base=0.01)
        def always_fail():
            raise ConnectionError("always fails")
        
        with pytest.raises(RetryExhaustedError):
            always_fail()


class TestRetryWithTimeout:
    """测试带超时的重试"""
    
    @pytest.mark.asyncio
    async def test_timeout_triggers_retry(self):
        """超时触发重试"""
        call_count = 0
        
        async def slow_then_fast():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                await asyncio.sleep(10)  # 触发超时
            return "success"
        
        result = await retry_with_timeout(
            slow_then_fast,
            timeout=0.1,
            max_attempts=3,
            backoff_base=0.01,
        )
        assert result == "success"
        assert call_count == 2
