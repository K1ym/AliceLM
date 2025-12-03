"""
自定义异常类
统一错误处理
"""

from typing import Optional, Dict, Any


class AppException(Exception):
    """应用基础异常"""
    
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


# ========== 认证相关异常 ==========

class AuthException(AppException):
    """认证异常基类"""
    pass


class InvalidCredentialsException(AuthException):
    """无效凭证"""
    
    def __init__(self, message: str = "邮箱或密码错误"):
        super().__init__(
            code="INVALID_CREDENTIALS",
            message=message,
            status_code=401,
        )


class TokenExpiredException(AuthException):
    """Token 过期"""
    
    def __init__(self):
        super().__init__(
            code="TOKEN_EXPIRED",
            message="Token 已过期",
            status_code=401,
        )


class UnauthorizedException(AuthException):
    """未授权"""
    
    def __init__(self, message: str = "未授权访问"):
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            status_code=401,
        )


# ========== 资源相关异常 ==========

class ResourceException(AppException):
    """资源异常基类"""
    pass


class NotFoundException(ResourceException):
    """资源不存在"""
    
    def __init__(self, resource: str, id: Any = None):
        message = f"{resource}不存在"
        if id:
            message = f"{resource} (ID: {id}) 不存在"
        super().__init__(
            code=f"{resource.upper()}_NOT_FOUND",
            message=message,
            status_code=404,
            details={"resource": resource, "id": id},
        )


class AlreadyExistsException(ResourceException):
    """资源已存在"""
    
    def __init__(self, resource: str, field: str = None, value: Any = None):
        message = f"{resource}已存在"
        if field and value:
            message = f"{resource} ({field}: {value}) 已存在"
        super().__init__(
            code=f"{resource.upper()}_ALREADY_EXISTS",
            message=message,
            status_code=409,
            details={"resource": resource, "field": field, "value": value},
        )


class ForbiddenException(ResourceException):
    """禁止访问"""
    
    def __init__(self, message: str = "无权访问此资源"):
        super().__init__(
            code="FORBIDDEN",
            message=message,
            status_code=403,
        )


# ========== 业务相关异常 ==========

class BusinessException(AppException):
    """业务异常基类"""
    pass


class ValidationException(BusinessException):
    """验证失败"""
    
    def __init__(self, message: str, field: str = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=422,
            details={"field": field} if field else {},
        )


class ProcessingException(BusinessException):
    """处理失败"""
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        super().__init__(
            code="PROCESSING_ERROR",
            message=message,
            status_code=500,
            details=details or {},
        )


class ExternalServiceException(BusinessException):
    """外部服务异常"""
    
    def __init__(self, service: str, message: str = None):
        super().__init__(
            code="EXTERNAL_SERVICE_ERROR",
            message=message or f"{service} 服务不可用",
            status_code=503,
            details={"service": service},
        )
