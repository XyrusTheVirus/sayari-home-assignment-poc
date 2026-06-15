"""FastAPI dependency factories."""

from collections.abc import AsyncIterator

from fastapi import Request

from document_pipeline.services.document_query_service import DocumentQueryService
from document_pipeline.services.processing_service import ProcessingService
from document_pipeline.services.rerun_service import RerunService


async def get_processing_service(request: Request) -> ProcessingService:
    """Return the app-scoped processing service."""

    return request.app.state.processing_service


async def get_rerun_service(request: Request) -> RerunService:
    """Return the app-scoped rerun service."""

    return request.app.state.rerun_service


async def get_query_service(request: Request) -> DocumentQueryService:
    """Return the app-scoped query service."""

    return request.app.state.query_service


async def lifespan_dependencies(request: Request) -> AsyncIterator[None]:
    """Reserved dependency hook for future per-request resources."""

    yield None
