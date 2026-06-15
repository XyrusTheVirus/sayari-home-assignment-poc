"""FastAPI application construction and runtime configuration."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from document_pipeline.api.controllers import (
    documents_controller,
    health_controller,
    process_controller,
)
from document_pipeline.api.exception_handlers import install_exception_handlers
from document_pipeline.api.middleware import install_middleware
from document_pipeline.config import get_settings
from document_pipeline.infrastructure.database import create_engine, create_session_factory
from document_pipeline.infrastructure.storage import create_object_store
from document_pipeline.infrastructure.temporal import create_temporal_client
from document_pipeline.integrations.mock_classifier import MockClassifier
from document_pipeline.integrations.mock_extractor import MockExtractor
from document_pipeline.logging import configure_logging
from document_pipeline.repositories.unit_of_work import UnitOfWorkFactory
from document_pipeline.services.document_query_service import DocumentQueryService
from document_pipeline.services.processing_service import ProcessingService
from document_pipeline.services.progress_service import ProgressService
from document_pipeline.services.rerun_service import RerunService

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and close process-scoped dependencies."""

    settings = get_settings()
    configure_logging(settings.log_level)
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    store = create_object_store(settings)
    temporal_client = await create_temporal_client(settings)
    extractor = MockExtractor(settings.mock_extractor_delay_ms)
    classifier = MockClassifier(settings.mock_classifier_delay_ms)
    uow_factory = UnitOfWorkFactory(session_factory)
    processing = ProcessingService(
        uow_factory=uow_factory,
        store=store,
        temporal_client=temporal_client,
        extractor=extractor,
        classifier=classifier,
        workflow_task_queue=settings.temporal_workflow_task_queue,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.store = store
    app.state.temporal_client = temporal_client
    app.state.processing_service = processing
    app.state.rerun_service = RerunService(uow_factory, store, processing)
    app.state.query_service = DocumentQueryService(uow_factory, ProgressService())
    logger.info("api dependencies initialized")
    try:
        yield
    finally:
        await store.close()
        await engine.dispose()


def create_app() -> FastAPI:
    """Create the FastAPI app with routers, middleware, and error handlers."""

    fastapi_app = FastAPI(
        title="Document Pipeline POC",
        version="0.1.0",
        lifespan=lifespan,
    )
    install_exception_handlers(fastapi_app)
    install_middleware(fastapi_app)
    fastapi_app.include_router(health_controller.router)
    fastapi_app.include_router(process_controller.router)
    fastapi_app.include_router(documents_controller.router)
    return fastapi_app


app = create_app()


def run() -> None:
    """Run the API server from the console script."""

    settings = get_settings()
    uvicorn.run("document_pipeline.api.main:app", host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    asyncio.run(asyncio.to_thread(run))
