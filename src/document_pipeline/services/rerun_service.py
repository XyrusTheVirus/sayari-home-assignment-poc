"""Application service for full rerun semantics."""

from document_pipeline.errors import DocumentNotFoundError, RunConflictError
from document_pipeline.integrations.object_store import ObjectStore
from document_pipeline.models.enums import RunStatus
from document_pipeline.repositories.unit_of_work import UnitOfWorkFactory
from document_pipeline.services.processing_service import ProcessingService, StartProcessingResult


class RerunService:
    """Creates isolated new runs while preserving the active result until completion."""

    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        store: ObjectStore,
        processing_service: ProcessingService,
    ) -> None:
        """Inject dependencies used to resolve prior source and start the new run."""

        self._uow_factory = uow_factory
        self._store = store
        self._processing_service = processing_service

    async def rerun(
        self, external_id: str, text: str | None, reuse_source: bool
    ) -> StartProcessingResult:
        """Start a new full run from new text or the latest source object."""

        has_text = text is not None and bool(text.strip())
        if has_text == reuse_source:
            raise RunConflictError("provide exactly one of text or reuse_source=true")
        if reuse_source:
            async with self._uow_factory.transaction() as uow:
                document = await uow.documents.get_by_external_id(external_id)
                if document is None:
                    raise DocumentNotFoundError(external_id)
                latest = await uow.runs.latest_for_document(document.id)
                if latest is None or latest.status == RunStatus.FAILED:
                    raise RunConflictError("no reusable source exists")
                text = await self._store.get_text(latest.source_uri)
        assert text is not None
        return await self._processing_service.start(external_id, text)
