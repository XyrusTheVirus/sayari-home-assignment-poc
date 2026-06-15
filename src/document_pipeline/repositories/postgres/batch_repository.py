"""PostgreSQL implementation of classification batch operations."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from document_pipeline.models.domain import BatchManifest
from document_pipeline.models.enums import WorkStatus
from document_pipeline.models.orm.classification_batch import ClassificationBatchORM
from document_pipeline.repositories.postgres.mappers import batch_manifest


class PostgresBatchRepository:
    """SQLAlchemy-backed classification batch repository."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the transaction-scoped session."""

        self._session = session

    async def bulk_create(self, batches: list[BatchManifest]) -> None:
        """Insert stable classification batches idempotently."""

        if not batches:
            return
        statement = insert(ClassificationBatchORM).values(
            [
                {
                    "id": item.id,
                    "run_id": item.run_id,
                    "chunk_id": item.chunk_id,
                    "start_local_index": item.start_local_index,
                    "end_local_index": item.end_local_index,
                    "status": item.status,
                    "processed_count": 0,
                    "attempts": 0,
                }
                for item in batches
            ]
        )
        await self._session.execute(statement.on_conflict_do_nothing())

    async def get(self, batch_id: UUID) -> BatchManifest | None:
        """Return a batch manifest by ID."""

        row = await self._session.get(ClassificationBatchORM, batch_id)
        return batch_manifest(row) if row else None

    async def mark_running(self, batch_id: UUID) -> bool:
        """Mark a batch running unless it is already completed."""

        row = await self._session.get(ClassificationBatchORM, batch_id, with_for_update=True)
        if row is None or row.status == WorkStatus.COMPLETED:
            return False
        row.status = WorkStatus.RUNNING
        row.started_at = row.started_at or datetime.now(UTC)
        row.attempts += 1
        return True

    async def mark_completed(self, batch_id: UUID, processed_count: int) -> bool:
        """Mark a batch complete with the count attributed to this attempt."""

        row = await self._session.get(ClassificationBatchORM, batch_id, with_for_update=True)
        if row is None or row.status == WorkStatus.COMPLETED:
            return False
        row.status = WorkStatus.COMPLETED
        row.processed_count = processed_count
        row.completed_at = row.completed_at or datetime.now(UTC)
        return True

    async def list_by_run(self, run_id: UUID) -> list[BatchManifest]:
        """List batches in deterministic chunk/range order."""

        rows = (
            await self._session.scalars(
                select(ClassificationBatchORM)
                .where(ClassificationBatchORM.run_id == run_id)
                .order_by(ClassificationBatchORM.chunk_id, ClassificationBatchORM.start_local_index)
            )
        ).all()
        return [batch_manifest(row) for row in rows]

    async def incomplete_count(self, run_id: UUID) -> int:
        """Count batches not durably completed."""

        value = await self._session.scalar(
            select(func.count())
            .select_from(ClassificationBatchORM)
            .where(ClassificationBatchORM.run_id == run_id, ClassificationBatchORM.status != WorkStatus.COMPLETED)
        )
        return int(value or 0)
