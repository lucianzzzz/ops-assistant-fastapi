"""统一异常处理中间件"""

import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.common.exceptions import OpsAssistantError

logger = logging.getLogger(__name__)


async def ops_error_handler(request: Request, exc: OpsAssistantError) -> JSONResponse:
    """处理业务异常

    Args:
        request: 请求对象
        exc: 业务异常

    Returns:
        标准错误响应
    """
    logger.warning(
        f"业务异常: {exc.code}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_code": exc.code,
            "error_message": exc.message
        }
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": exc.code,
                "message": exc.message
            }
        }
    )


async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
    """处理参数验证异常

    Args:
        request: 请求对象
        exc: Pydantic 验证异常

    Returns:
        标准错误响应
    """
    errors = exc.errors()
    logger.warning(
        f"参数验证失败: {len(errors)} 个错误",
        extra={
            "path": request.url.path,
            "method": request.method,
            "validation_errors": errors
        }
    )

    # 格式化错误信息
    error_messages = []
    for error in errors:
        field = ".".join(str(loc) for loc in error["loc"])
        message = error["msg"]
        error_messages.append(f"{field}: {message}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "; ".join(error_messages)
            }
        }
    )


async def global_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """捕获所有未处理的异常

    Args:
        request: 请求对象
        exc: 异常对象

    Returns:
        标准错误响应
    """
    logger.error(
        f"未处理异常: {type(exc).__name__}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__,
            "error_message": str(exc)
        },
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "服务内部错误"
            }
        }
    )
