"""
全局异常处理器
统一错误响应格式
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from packages.logging import get_logger
from .exceptions import AppException

logger = get_logger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """处理应用自定义异常"""
    logger.warning(
        "app_exception",
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        path=request.url.path,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理未捕获的异常"""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务器内部错误",
                "details": {},
            }
        },
    )


def register_exception_handlers(app):
    """注册异常处理器到 FastAPI 应用"""
    app.add_exception_handler(AppException, app_exception_handler)
    # 生产环境可以启用通用异常处理
    # app.add_exception_handler(Exception, generic_exception_handler)
