"""Application service for initial document processing requests."""

import hashlib
from dataclasses import dataclass
from uuid import UUID

from temporalio.client import Client

from document_pipeline.errors import RetryableInfrastructureError
from document_pipeline.integrations.classifier import Classifier
from document_pipeline.integrations.extractor import Extractor
from document_pipeline.integrations.object_store import ObjectStore
from document_pipeline.models.domain import RunRecord
from document_pipeline.models.enums import RunStatus
from document_pipeline.repositories.unit_of_work import UnitOfWorkFactory
from document_pipeline.workflows.contracts import DocumentProcessingWorkflowInput
from document_pipeline.workflows.document_processing_workflow import DocumentProcessingWorkflow


@dataclass(frozen=True, slots=True)
class StartProcessingResult:
    """Result returned after a run is created and workflow start is requested."""

    document_id: str
    run_id: UUID
    version: int
    status: RunStatus
    status_url: str


class ProcessingService:
    """Creates immutable source objects, versioned runs, and Temporal workflows."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        store: ObjectStore,
        temporal_client: Client,
        extractor: Extractor,
        classifier: Classifier,
        workflow_task_queue: str,
    ) -> None:
        """Inject persistence, storage, providers, and orchestration dependencies."""

        self._uow_factory = uow_factory
        self._store = store
        self._temporal_client = temporal_client
        self._extractor = extractor
        self._classifier = classifier
        self._workflow_task_queue = workflow_task_queue

    async def start(self, external_id: str, text: str) -> StartProcessingResult:
        """Create a new versioned run and start asynchronous processing."""

        checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
        async with self._uow_factory.transaction() as uow:
            document = await uow.documents.create_if_absent(external_id)
            await uow.documents.lock_by_id(document.id)
            version = await uow.runs.next_version_for_document(document.id)
            source_key = f"documents/{external_id}/runs/{version}/source.txt"
            source_uri = await self._store.put_text(source_key, text)
            run = await uow.runs.create(
                document_id=document.id,
                version=version,
                source_uri=source_uri,
                source_checksum=checksum,
                extractor_version=self._extractor.version,
                classifier_version=self._classifier.version,
                model_version=getattr(self._classifier, "model_version", None),
                prompt_version=getattr(self._classifier, "prompt_version", None),
            )
        await self._start_workflow_or_mark_failed(run)
        return StartProcessingResult(
            document_id=external_id,
            run_id=run.id,
            version=run.version,
            status=run.status,
            status_url=f"/documents/{external_id}/status",
        )

    async def _start_workflow_or_mark_failed(self, run: RunRecord) -> None:
        """Start Temporal and persist explicit failure if start fails after run creation."""

        try:
            await self._temporal_client.start_workflow(
                DocumentProcessingWorkflow.run,
                DocumentProcessingWorkflowInput(run_id=run.id),
                id=f"document-run/{run.id}",
                task_queue=self._workflow_task_queue,
            )
        except Exception as exc:
            async with self._uow_factory.transaction() as uow:
                await uow.runs.mark_failed(run.id, "workflow_start_failed", "Temporal workflow could not be started")
            raise RetryableInfrastructureError("Temporal workflow could not be started") from exc
