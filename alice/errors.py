"""
Alice 统一错误类型

所有模块应使用这些错误类型，而不是直接 except Exception。
这样可以区分可重试错误和不可重试错误。
"""

from typing import Optional, Any


class AliceError(Exception):
    """Alice 基础错误类"""
    
    def __init__(self, message: str, details: Optional[Any] = None):
        super().__init__(message)
        self.message = message
        self.details = details
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


# ============================================================
# 配置相关错误 - 不可重试，应立即失败
# ============================================================

class ConfigError(AliceError):
    """配置错误 - 立即失败，不重试"""
    pass


class PromptNotFoundError(ConfigError):
    """Prompt 未找到"""
    
    def __init__(self, key: str):
        super().__init__(f"Prompt not found: {key}", key)


class ModelNotFoundError(ConfigError):
    """模型配置未找到"""
    
    def __init__(self, model_id: str):
        super().__init__(f"Model not found: {model_id}", model_id)


class ToolNotFoundError(ConfigError):
    """工具未找到"""
    
    def __init__(self, tool_name: str):
        super().__init__(f"Tool not found: {tool_name}", tool_name)


# ============================================================
# 网络/外部服务错误 - 可重试
# ============================================================

class NetworkError(AliceError):
    """网络错误 - 可重试"""
    retryable = True


class TimeoutError(NetworkError):
    """超时错误 - 可重试"""
    pass


class RateLimitError(NetworkError):
    """限流错误 - 可重试（需要等待）"""
    
    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


# ============================================================
# LLM 相关错误
# ============================================================

class LLMError(AliceError):
    """LLM 调用错误"""
    pass


class LLMConnectionError(LLMError, NetworkError):
    """LLM 连接错误 - 可重试"""
    retryable = True


class LLMResponseError(LLMError):
    """LLM 响应解析错误 - 不可重试"""
    pass


class LLMContextTooLongError(LLMError):
    """上下文超长 - 需要压缩后重试"""
    pass


# ============================================================
# Agent 相关错误
# ============================================================

class AgentError(AliceError):
    """Agent 执行错误"""
    pass


class ToolExecutionError(AgentError):
    """工具执行错误"""
    
    def __init__(self, tool_name: str, message: str, original_error: Optional[Exception] = None):
        super().__init__(f"Tool '{tool_name}' failed: {message}")
        self.tool_name = tool_name
        self.original_error = original_error


class PlanningError(AgentError):
    """计划生成错误"""
    pass


class MaxIterationsError(AgentError):
    """超过最大迭代次数"""
    
    def __init__(self, max_iterations: int):
        super().__init__(f"Exceeded max iterations: {max_iterations}")
        self.max_iterations = max_iterations


# ============================================================
# RAG 相关错误
# ============================================================

class RAGError(AliceError):
    """RAG 检索错误"""
    pass


class EmbeddingError(RAGError):
    """Embedding 生成错误"""
    pass


class IndexError(RAGError):
    """索引错误"""
    pass


class SearchError(RAGError):
    """搜索错误"""
    pass


# ============================================================
# 工具函数
# ============================================================

def is_retryable(error: Exception) -> bool:
    """判断错误是否可重试"""
    if isinstance(error, AliceError):
        return getattr(error, 'retryable', False)
    # 常见的可重试异常
    import httpx
    return isinstance(error, (
        ConnectionError,
        TimeoutError,
        httpx.TimeoutException,
        httpx.ConnectError,
    ))
