"""FastAPI exception handlers for stable client-safe errors."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from starlette import status

from document_pipeline.errors import PipelineError
from document_pipeline.logging import request_id_var


def install_exception_handlers(app: FastAPI) -> None:
    """Register centralized error mappers on the FastAPI app."""

    @app.exception_handler(PipelineError)
    async def pipeline_error_handler(_request: Request, exc: PipelineError) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "detail": str(exc), "request_id": request_id_var.get()},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> ORJSONResponse:
        return ORJSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "detail": exc.errors(),
                "request_id": request_id_var.get(),
            },
        )
