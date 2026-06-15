"""PostgreSQL implementation of extraction chunk operations."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from document_pipeline.models.domain import ChunkManifest
from document_pipeline.models.enums import WorkStatus
from document_pipeline.models.orm.document_chunk import DocumentChunkORM
from document_pipeline.models.orm.document_run import DocumentRunORM
from document_pipeline.repositories.postgres.mappers import chunk_manifest


class PostgresChunkRepository:
    """SQLAlchemy-backed chunk repository."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the transaction-scoped session."""

        self._session = session

    async def bulk_create(self, chunks: list[ChunkManifest]) -> None:
        """Insert deterministic chunk manifests idempotently."""

        if not chunks:
            return
        statement = insert(DocumentChunkORM).values(
            [
                {
                    "id": item.id,
                    "run_id": item.run_id,
                    "chunk_index": item.chunk_index,
                    "object_uri": item.object_uri,
                    "read_start": item.read_start,
                    "read_end": item.read_end,
                    "core_start": item.core_start,
                    "core_end": item.core_end,
                    "status": item.status,
                    "attempts": 0,
                    "extracted_token_count": 0,
                }
                for item in chunks
            ]
        )
        await self._session.execute(statement.on_conflict_do_nothing())

    async def get(self, chunk_id: UUID) -> ChunkManifest | None:
        """Return a chunk manifest by ID."""

        row = await self._session.get(DocumentChunkORM, chunk_id)
        return chunk_manifest(row) if row else None

    async def mark_running(self, chunk_id: UUID) -> bool:
        """Mark a pending/failed chunk as running and increment attempts."""

        row = await self._session.get(DocumentChunkORM, chunk_id, with_for_update=True)
        if row is None:
            return False
        if row.status == WorkStatus.COMPLETED:
            return False
        row.status = WorkStatus.RUNNING
        row.started_at = row.started_at or datetime.now(UTC)
        row.attempts += 1
        return True

    async def mark_completed(self, chunk_id: UUID, token_count: int) -> bool:
        """Mark a chunk complete and increment completed chunk count once."""

        row = await self._session.get(DocumentChunkORM, chunk_id, with_for_update=True)
        if row is None or row.status == WorkStatus.COMPLETED:
            return False
        row.status = WorkStatus.COMPLETED
        row.extracted_token_count = token_count
        row.completed_at = row.completed_at or datetime.now(UTC)
        run = await self._session.get(DocumentRunORM, row.run_id, with_for_update=True)
        if run is not None:
            run.completed_chunks += 1
        return True

    async def list_by_run(self, run_id: UUID) -> list[ChunkManifest]:
        """List chunks for a run in deterministic order."""

        rows = (
            await self._session.scalars(
                select(DocumentChunkORM).where(DocumentChunkORM.run_id == run_id).order_by(DocumentChunkORM.chunk_index)
            )
        ).all()
        return [chunk_manifest(row) for row in rows]

    async def incomplete_count(self, run_id: UUID) -> int:
        """Count chunks not durably completed."""

        value = await self._session.scalar(
            select(func.count())
            .select_from(DocumentChunkORM)
            .where(DocumentChunkORM.run_id == run_id, DocumentChunkORM.status != WorkStatus.COMPLETED)
        )
        return int(value or 0)
