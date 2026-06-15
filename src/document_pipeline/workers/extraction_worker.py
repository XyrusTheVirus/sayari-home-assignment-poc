"""Temporal worker entry point for extraction activities."""

import asyncio
import logging

from temporalio.worker import Worker

from document_pipeline.config import get_settings
from document_pipeline.infrastructure.temporal import create_temporal_client
from document_pipeline.logging import configure_logging
from document_pipeline.workflows.activities.dependencies import create_activity_dependencies
from document_pipeline.workflows.activities.extraction_activities import extract_chunk_activity
from document_pipeline.workflows.activities.run_activities import configure

logger = logging.getLogger(__name__)


async def main() -> None:
    """Start the extraction worker on the extraction task queue."""

    settings = get_settings()
    configure_logging(settings.log_level)
    dependencies = create_activity_dependencies()
    configure(dependencies)
    client = await create_temporal_client(settings)
    worker = Worker(
        client,
        task_queue=settings.temporal_extraction_task_queue,
        activities=[extract_chunk_activity],
        max_concurrent_activities=settings.extraction_worker_concurrency,
    )
    logger.info("extraction worker started")
    try:
        await worker.run()
    finally:
        await dependencies.close()


def run() -> None:
    """Synchronous console-script entry point."""

    asyncio.run(main())


if __name__ == "__main__":
    run()
