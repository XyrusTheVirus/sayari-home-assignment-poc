"""Application service for document status and token queries."""

from uuid import UUID

from document_pipeline.errors import DocumentNotFoundError, RunConflictError, RunNotFoundError
from document_pipeline.models.domain import StatusView, TokenView
from document_pipeline.repositories.interfaces import TokenFilters
from document_pipeline.repositories.unit_of_work import UnitOfWorkFactory
from document_pipeline.services.cursor import decode_cursor, encode_cursor
from document_pipeline.services.progress_service import ProgressService


class DocumentQueryService:
    """Resolves active/latest/specific run semantics for API reads."""

    def __init__(self, uow_factory: UnitOfWorkFactory, progress: ProgressService) -> None:
        """Inject read repositories and progress calculator."""

        self._uow_factory = uow_factory
        self._progress = progress

    async def status(self, external_id: str, run_id: UUID | None = None) -> StatusView:
        """Return status for a specific run or the latest run when omitted."""

        async with self._uow_factory.transaction() as uow:
            document = await uow.documents.get_by_external_id(external_id)
            if document is None:
                raise DocumentNotFoundError(external_id)
            run = (
                await uow.runs.get(run_id)
                if run_id
                else await uow.runs.latest_for_document(document.id)
            )
            if run is None or run.document_id != document.id:
                raise RunNotFoundError(str(run_id))
            return StatusView(
                document_id=external_id,
                run_id=run.id,
                active_run_id=document.active_run_id,
                version=run.version,
                status=run.status,
                extraction=self._progress.extraction_progress(run),
                classification=self._progress.classification_progress(run),
                error_code=run.error_code,
                error_detail=run.error_detail,
            )

    async def tokens(
        self,
        external_id: str,
        filters: TokenFilters,
        limit: int,
        cursor: str | None,
        run_id: UUID | None = None,
    ) -> tuple[list[TokenView], str | None]:
        """Return active or historical tokens using keyset pagination."""

        async with self._uow_factory.transaction() as uow:
            document = await uow.documents.get_by_external_id(external_id)
            if document is None:
                raise DocumentNotFoundError(external_id)
            resolved_run_id = run_id or document.active_run_id
            if resolved_run_id is None:
                raise RunConflictError("document has no completed active run")
            run = await uow.runs.get(resolved_run_id)
            if run is None or run.document_id != document.id:
                raise RunNotFoundError(str(resolved_run_id))
            items, next_cursor = await uow.tokens.query(
                resolved_run_id,
                filters,
                limit,
                decode_cursor(cursor),
            )
        return items, encode_cursor(next_cursor)
