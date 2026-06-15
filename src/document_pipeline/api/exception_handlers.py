"""FastAPI exception handlers for stable, extensible client-safe errors."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from document_pipeline.errors import PipelineError
from document_pipeline.logging import request_id_var

ErrorDetailsFactory = Callable[[Exception], Any | None]


@dataclass(frozen=True, slots=True)
class ErrorHandlerConfig:
    """Configuration for mapping one custom exception type to public JSON."""

    status_code: int
    code: str
    message: str | Callable[[Exception], str]
    details: ErrorDetailsFactory | None = None


def build_error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
) -> ORJSONResponse:
    """Build the standard pretty JSON error envelope."""

    error: dict[str, Any] = {
        "status_code": status_code,
        "code": code,
        "message": message,
        "request_id": request_id_var.get(),
    }
    if details is not None:
        error["details"] = details
    return ORJSONResponse(status_code=status_code, content={"error": error})


def register_error_handler(
    app: FastAPI,
    exception_type: type[Exception],
    config: ErrorHandlerConfig,
) -> None:
    """Register an extensible custom exception-to-JSON mapper."""

    @app.exception_handler(exception_type)
    async def custom_error_handler(_request: Request, exc: Exception) -> ORJSONResponse:
        message = config.message(exc) if callable(config.message) else config.message
        details = config.details(exc) if config.details is not None else None
        return build_error_response(
            status_code=config.status_code,
            code=config.code,
            message=message,
            details=details,
        )


def install_exception_handlers(app: FastAPI) -> None:
    """Register centralized error mappers on the FastAPI app."""

    @app.exception_handler(PipelineError)
    async def pipeline_error_handler(_request: Request, exc: PipelineError) -> ORJSONResponse:
        return build_error_response(
            status_code=exc.status_code,
            code=exc.code,
            message=str(exc) or exc.code.replace("_", " "),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(
        _request: Request, exc: StarletteHTTPException
    ) -> ORJSONResponse:
        return build_error_response(
            status_code=exc.status_code,
            code="http_error",
            message=str(exc.detail) if exc.detail else "HTTP request failed.",
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> ORJSONResponse:
        return build_error_response(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="validation_error",
            message="Request validation failed.",
            details=exc.errors(),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, _exc: Exception) -> ORJSONResponse:
        return build_error_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="internal_server_error",
            message="An unexpected server error occurred.",
        )
