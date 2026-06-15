"""Temporal worker entry point for workflow orchestration activities."""

import asyncio
import logging

from temporalio.worker import Worker

from document_pipeline.config import get_settings
from document_pipeline.infrastructure.temporal import create_temporal_client
from document_pipeline.logging import configure_logging
from document_pipeline.workflows.activities.dependencies import create_activity_dependencies
from document_pipeline.workflows.activities.run_activities import (
    configure,
    finalize_extraction_activity,
    finalize_run_activity,
    initialize_run_activity,
    record_run_failure_activity,
    start_classification_activity,
)
from document_pipeline.workflows.document_processing_workflow import DocumentProcessingWorkflow

logger = logging.getLogger(__name__)


async def main() -> None:
    """Start the workflow worker and register only orchestration activities."""

    settings = get_settings()
    configure_logging(settings.log_level)
    dependencies = create_activity_dependencies()
    configure(dependencies)
    client = await create_temporal_client(settings)
    worker = Worker(
        client,
        task_queue=settings.temporal_workflow_task_queue,
        workflows=[DocumentProcessingWorkflow],
        activities=[
            initialize_run_activity,
            finalize_extraction_activity,
            start_classification_activity,
            finalize_run_activity,
            record_run_failure_activity,
        ],
    )
    logger.info("workflow worker started")
    try:
        await worker.run()
    finally:
        await dependencies.close()


def run() -> None:
    """Synchronous console-script entry point."""

    asyncio.run(main())


if __name__ == "__main__":
    run()
