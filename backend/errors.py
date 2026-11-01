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
