"""PostgreSQL implementation of processing run operations."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from document_pipeline.errors import InvalidRunStateError
from document_pipeline.models.domain import RunRecord
from document_pipeline.models.enums import RunStatus
from document_pipeline.models.orm.document_run import DocumentRunORM
from document_pipeline.repositories.postgres.mappers import run_record


class PostgresRunRepository:
    """SQLAlchemy-backed run repository with guarded state transitions."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the transaction-scoped session."""

        self._session = session

    async def create(
        self,
        document_id: UUID,
        version: int,
        source_uri: str,
        source_checksum: str,
        extractor_version: str,
        classifier_version: str,
        model_version: str | None,
        prompt_version: str | None,
    ) -> RunRecord:
        """Create a PENDING versioned run."""

        row = DocumentRunORM(
            document_id=document_id,
            version=version,
            source_uri=source_uri,
            source_checksum=source_checksum,
            status=RunStatus.PENDING,
            total_chunks=0,
            completed_chunks=0,
            classified_tokens=0,
            extractor_version=extractor_version,
            classifier_version=classifier_version,
            model_version=model_version,
            prompt_version=prompt_version,
        )
        self._session.add(row)
        await self._session.flush()
        return run_record(row)

    async def get(self, run_id: UUID) -> RunRecord | None:
        """Return a run by internal ID."""

        row = await self._session.get(DocumentRunORM, run_id)
        return run_record(row) if row else None

    async def latest_for_document(self, document_id: UUID) -> RunRecord | None:
        """Return the highest-version run for a document."""

        row = await self._session.scalar(
            select(DocumentRunORM)
            .where(DocumentRunORM.document_id == document_id)
            .order_by(DocumentRunORM.version.desc())
            .limit(1)
        )
        return run_record(row) if row else None

    async def next_version_for_document(self, document_id: UUID) -> int:
        """Return the next monotonic version while caller holds the document lock."""

        value = await self._session.scalar(
            select(func.coalesce(func.max(DocumentRunORM.version), 0) + 1).where(
                DocumentRunORM.document_id == document_id
            )
        )
        return int(value or 1)

    async def transition(self, run_id: UUID, expected: RunStatus, target: RunStatus) -> None:
        """Move a run between states only if the current state matches."""

        row = await self._session.get(DocumentRunORM, run_id, with_for_update=True)
        if row is None or row.status != expected:
            raise InvalidRunStateError(f"run {run_id} is not in state {expected}")
        row.status = target
        row.updated_at = datetime.now(UTC)

    async def mark_extraction_started(self, run_id: UUID, total_chunks: int) -> None:
        """Set extraction start metadata once and transition to EXTRACTING."""

        row = await self._session.get(DocumentRunORM, run_id, with_for_update=True)
        if row is None:
            raise InvalidRunStateError(f"run {run_id} not found")
        if row.status == RunStatus.PENDING:
            row.status = RunStatus.EXTRACTING
        elif row.status != RunStatus.EXTRACTING:
            raise InvalidRunStateError(f"run {run_id} cannot start extraction from {row.status}")
        row.total_chunks = total_chunks
        row.extraction_started_at = row.extraction_started_at or datetime.now(UTC)

    async def finalize_extraction(self, run_id: UUID, total_tokens: int) -> None:
        """Record exact token count and move to classification-pending state."""

        row = await self._session.get(DocumentRunORM, run_id, with_for_update=True)
        if row is None or row.status != RunStatus.EXTRACTING:
            raise InvalidRunStateError(f"run {run_id} cannot finalize extraction")
        row.total_tokens = total_tokens
        row.extraction_completed_at = row.extraction_completed_at or datetime.now(UTC)
        row.status = RunStatus.CLASSIFICATION_PENDING

    async def mark_classification_started(self, run_id: UUID) -> None:
        """Set classification start metadata once."""

        row = await self._session.get(DocumentRunORM, run_id, with_for_update=True)
        if row is None or row.status not in {RunStatus.CLASSIFICATION_PENDING, RunStatus.CLASSIFYING}:
            raise InvalidRunStateError(f"run {run_id} cannot start classification")
        row.status = RunStatus.CLASSIFYING
        row.classification_started_at = row.classification_started_at or datetime.now(UTC)

    async def finalize_completed(self, run_id: UUID) -> None:
        """Mark a fully classified run complete after counter validation."""

        row = await self._session.get(DocumentRunORM, run_id, with_for_update=True)
        if row is None or row.status != RunStatus.CLASSIFYING:
            raise InvalidRunStateError(f"run {run_id} cannot complete")
        if row.total_tokens is None or row.classified_tokens != row.total_tokens:
            raise InvalidRunStateError("classification progress is incomplete")
        row.classification_completed_at = row.classification_completed_at or datetime.now(UTC)
        row.status = RunStatus.COMPLETED

    async def mark_failed(self, run_id: UUID, code: str, detail: str) -> None:
        """Expose sanitized terminal failure information without overwriting completion."""

        row = await self._session.get(DocumentRunORM, run_id, with_for_update=True)
        if row is None or row.status == RunStatus.COMPLETED:
            return
        row.status = RunStatus.FAILED
        row.error_code = code[:128]
        row.error_detail = detail[:1_000]
