"""FastAPI middleware registration."""

import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from document_pipeline.logging import request_id_var


def install_middleware(app: FastAPI) -> None:
    """Register all application middleware in one place."""

    @app.middleware("http")
    async def request_id_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Assign or propagate request IDs and include them in responses/logs."""

        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
            response.headers["x-request-id"] = request_id
            return response
        finally:
            request_id_var.reset(token)
