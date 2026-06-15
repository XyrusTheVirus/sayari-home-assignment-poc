"""Recompute safe derived counters for a run."""

import asyncio
import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from document_pipeline.config import get_settings
from document_pipeline.infrastructure.database import create_engine, create_session_factory
from document_pipeline.models.enums import TokenStatus, WorkStatus
from document_pipeline.models.orm.classification_batch import ClassificationBatchORM
from document_pipeline.models.orm.document_chunk import DocumentChunkORM
from document_pipeline.models.orm.document_run import DocumentRunORM
from document_pipeline.models.orm.token import TokenORM

logger = logging.getLogger(__name__)


class ReconciliationService:
    """Repairs derived progress counters from durable child rows."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store a SQLAlchemy async session factory."""

        self._session_factory = session_factory

    async def reconcile(self, run_id: UUID, repair: bool = False) -> dict[str, int]:
        """Report or repair chunk, token, and batch counters for one run."""

        async with self._session_factory() as session:
            completed_chunks = int(
                await session.scalar(
                    select(func.count())
                    .select_from(DocumentChunkORM)
                    .where(
                        DocumentChunkORM.run_id == run_id,
                        DocumentChunkORM.status == WorkStatus.COMPLETED,
                    )
                )
                or 0
            )
            total_tokens = int(
                await session.scalar(
                    select(func.count()).select_from(TokenORM).where(TokenORM.run_id == run_id)
                )
                or 0
            )
            classified_tokens = int(
                await session.scalar(
                    select(func.count())
                    .select_from(TokenORM)
                    .where(
                        TokenORM.run_id == run_id,
                        TokenORM.classification_status == TokenStatus.COMPLETED,
                    )
                )
                or 0
            )
            completed_batches = int(
                await session.scalar(
                    select(func.count())
                    .select_from(ClassificationBatchORM)
                    .where(
                        ClassificationBatchORM.run_id == run_id,
                        ClassificationBatchORM.status == WorkStatus.COMPLETED,
                    )
                )
                or 0
            )
            if repair:
                run = await session.get(DocumentRunORM, run_id, with_for_update=True)
                if run is not None:
                    run.completed_chunks = completed_chunks
                    run.total_tokens = (
                        total_tokens if run.extraction_completed_at else run.total_tokens
                    )
                    run.classified_tokens = classified_tokens
                    await session.commit()
            return {
                "completed_chunks": completed_chunks,
                "total_tokens": total_tokens,
                "classified_tokens": classified_tokens,
                "completed_batches": completed_batches,
            }


async def main() -> None:
    """Placeholder CLI entry point documenting the reconciliation command."""

    settings = get_settings()
    engine = create_engine(settings)
    try:
        _ = ReconciliationService(create_session_factory(engine))
        logger.info("Use ReconciliationService.reconcile(run_id, repair=True) from an ops shell.")
    finally:
        await engine.dispose()


def run() -> None:
    """Run the async reconciliation CLI."""

    asyncio.run(main())
