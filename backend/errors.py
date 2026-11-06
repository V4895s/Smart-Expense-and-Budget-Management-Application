"""Standard error envelope { code, message } (SAD 4.4)."""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _friendly(error: dict) -> str:
    location = [str(part) for part in error.get("loc", []) if part not in ("body", "query", "path")]
    field = ".".join(location) or "request"
    message = str(error.get("msg", "Invalid value.")).removeprefix("Value error, ")
    return f"{field}: {message}"


async def validation_error_handler(request: Request, exc: RequestValidationError):
    messages = [_friendly(error) for error in exc.errors()]
    summary = "; ".join(messages)
    return JSONResponse(
        status_code=400,
        content={
            "code": "VALIDATION_ERROR",
            "message": summary,
            # kept so existing frontend code that reads `detail` keeps working
            "detail": summary,
            "errors": messages,
        },
    )


# ---- Availability / reliability handlers (SEA-NF-002, SAD 4.4) -------------------------
import logging  # noqa: E402

from fastapi.responses import JSONResponse as _JSONResponse  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402
from starlette.exceptions import HTTPException as StarletteHTTPException  # noqa: E402

_logger = logging.getLogger(__name__)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Add { code, message } to every HTTP error; `detail` kept for the existing frontend."""
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    return _JSONResponse(
        status_code=exc.status_code,
        content={"code": f"HTTP_{exc.status_code}", "message": message, "detail": message},
        headers=getattr(exc, "headers", None),
    )


async def database_error_handler(request: Request, exc: SQLAlchemyError):
    _logger.error("Unhandled database error on %s: %s", request.url.path, type(exc).__name__)
    message = "The service is temporarily unavailable. Please try again shortly."
    return _JSONResponse(
        status_code=503,
        content={"code": "SERVICE_UNAVAILABLE", "message": message, "detail": message},
        headers={"Retry-After": "10"},
    )


async def unhandled_error_handler(request: Request, exc: Exception):
    _logger.exception("Unhandled error on %s", request.url.path)
    message = "Something went wrong. Please try again."
    return _JSONResponse(
        status_code=500,
        content={"code": "INTERNAL_ERROR", "message": message, "detail": message},
    )
