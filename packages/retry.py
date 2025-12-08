"""
重试和超时机制

提供装饰器和上下文管理器用于重试可恢复的错误。
"""

import asyncio
import time
from functools import wraps
from typing import Callable, Tuple, Type, Optional, TypeVar, Any
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryExhaustedError(Exception):
    """重试次数耗尽"""
    
    def __init__(self, attempts: int, last_error: Exception):
        super().__init__(f"Retry exhausted after {attempts} attempts")
        self.attempts = attempts
        self.last_error = last_error


def with_retry(
    max_attempts: int = 3,
    backoff_base: float = 1.0,
    backoff_max: float = 30.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """
    异步重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        backoff_base: 退避基数（秒）
        backoff_max: 最大退避时间（秒）
        retryable_exceptions: 可重试的异常类型
        on_retry: 重试时的回调函数
    
    Usage:
        @with_retry(max_attempts=3)
        async def call_api():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_error: Optional[Exception] = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_error = e
                    
                    if attempt >= max_attempts:
                        logger.warning(
                            f"Retry exhausted for {func.__name__}",
                            extra={"attempts": attempt, "error": str(e)}
                        )
                        raise RetryExhaustedError(attempt, e) from e
                    
                    # 计算退避时间（指数退避 + 抖动）
                    import random
                    wait = min(
                        backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 1),
                        backoff_max
                    )
                    
                    logger.info(
                        f"Retrying {func.__name__}",
                        extra={"attempt": attempt, "wait": wait, "error": str(e)}
                    )
                    
                    if on_retry:
                        on_retry(e, attempt)
                    
                    await asyncio.sleep(wait)
            
            # Should not reach here
            raise RetryExhaustedError(max_attempts, last_error)
        
        return wrapper
    return decorator


def with_retry_sync(
    max_attempts: int = 3,
    backoff_base: float = 1.0,
    backoff_max: float = 30.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    同步重试装饰器
    
    Usage:
        @with_retry_sync(max_attempts=3)
        def call_api():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_error: Optional[Exception] = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_error = e
                    
                    if attempt >= max_attempts:
                        raise RetryExhaustedError(attempt, e) from e
                    
                    import random
                    wait = min(
                        backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 1),
                        backoff_max
                    )
                    
                    logger.info(f"Retrying {func.__name__}, attempt {attempt}, wait {wait:.2f}s")
                    time.sleep(wait)
            
            raise RetryExhaustedError(max_attempts, last_error)
        
        return wrapper
    return decorator


class Timeout:
    """
    超时上下文管理器（仅适用于异步）
    
    Usage:
        async with Timeout(seconds=10):
            await long_running_task()
    """
    
    def __init__(self, seconds: float):
        self.seconds = seconds
        self._task: Optional[asyncio.Task] = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass
    
    @staticmethod
    async def run(coro, seconds: float):
        """运行协程，超时抛出 asyncio.TimeoutError"""
        return await asyncio.wait_for(coro, timeout=seconds)


async def retry_with_timeout(
    coro_func: Callable[..., Any],
    *args,
    timeout: float = 30.0,
    max_attempts: int = 3,
    backoff_base: float = 1.0,
    **kwargs
) -> Any:
    """
    带超时的重试
    
    Usage:
        result = await retry_with_timeout(
            call_api, arg1, arg2,
            timeout=10.0,
            max_attempts=3
        )
    """
    last_error: Optional[Exception] = None
    
    for attempt in range(1, max_attempts + 1):
        try:
            return await asyncio.wait_for(
                coro_func(*args, **kwargs),
                timeout=timeout
            )
        except asyncio.TimeoutError as e:
            last_error = e
            logger.warning(f"Timeout on attempt {attempt}")
        except Exception as e:
            last_error = e
            logger.warning(f"Error on attempt {attempt}: {e}")
        
        if attempt >= max_attempts:
            raise RetryExhaustedError(attempt, last_error)
        
        import random
        wait = min(backoff_base * (2 ** (attempt - 1)) + random.uniform(0, 1), 30.0)
        await asyncio.sleep(wait)
    
    raise RetryExhaustedError(max_attempts, last_error)
