"""Deterministic Temporal workflow for document processing."""

import asyncio
from collections.abc import Sequence
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

from document_pipeline.workflows.contracts import DocumentProcessingWorkflowInput


@workflow.defn
class DocumentProcessingWorkflow:
    """Coordinates extraction barrier, classification batches, and publication."""

    @workflow.run
    async def run(self, value: DocumentProcessingWorkflowInput) -> None:
        """Run the complete two-stage processing lifecycle for one run ID."""

        retry_policy = RetryPolicy(
            maximum_attempts=5,
            initial_interval=timedelta(seconds=1),
            maximum_interval=timedelta(seconds=20),
        )
        try:
            chunks = await workflow.execute_activity(
                "initialize_run_activity",
                value.run_id,
                task_queue="document-workflows",
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=retry_policy,
            )
            for window in _windows(chunks, 4):
                await asyncio.gather(
                    *[
                        workflow.execute_activity(
                            "extract_chunk_activity",
                            chunk_id,
                            task_queue="extraction",
                            start_to_close_timeout=timedelta(minutes=5),
                            retry_policy=retry_policy,
                        )
                        for chunk_id in window
                    ]
                )
            batches = await workflow.execute_activity(
                "finalize_extraction_activity",
                value.run_id,
                task_queue="document-workflows",
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=retry_policy,
            )
            await workflow.execute_activity(
                "start_classification_activity",
                value.run_id,
                task_queue="document-workflows",
                start_to_close_timeout=timedelta(minutes=1),
                retry_policy=retry_policy,
            )
            for window in _windows(batches, 4):
                await asyncio.gather(
                    *[
                        workflow.execute_activity(
                            "classify_batch_activity",
                            batch_id,
                            task_queue="classification",
                            heartbeat_timeout=timedelta(seconds=15),
                            start_to_close_timeout=timedelta(minutes=10),
                            retry_policy=retry_policy,
                        )
                        for batch_id in window
                    ]
                )
            await workflow.execute_activity(
                "finalize_run_activity",
                value.run_id,
                task_queue="document-workflows",
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=retry_policy,
            )
        except Exception as exc:
            await workflow.execute_activity(
                "record_run_failure_activity",
                (value.run_id, type(exc).__name__, str(exc)[:500]),
                task_queue="document-workflows",
                start_to_close_timeout=timedelta(minutes=1),
            )
            raise


def _windows[T](values: Sequence[T], size: int) -> list[list[T]]:
    """Return bounded deterministic windows for workflow fan-out."""

    return [list(values[index : index + size]) for index in range(0, len(values), size)]
