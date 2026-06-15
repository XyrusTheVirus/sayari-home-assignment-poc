"""Unit-of-work helpers for explicit service transaction boundaries."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from document_pipeline.repositories.postgres.batch_repository import PostgresBatchRepository
from document_pipeline.repositories.postgres.chunk_repository import PostgresChunkRepository
from document_pipeline.repositories.postgres.document_repository import PostgresDocumentRepository
from document_pipeline.repositories.postgres.run_repository import PostgresRunRepository
from document_pipeline.repositories.postgres.token_repository import PostgresTokenRepository


class UnitOfWork:
    """Repository bundle bound to one async SQLAlchemy session."""

    def __init__(self, session: AsyncSession) -> None:
        """Create repositories sharing the same transaction/session."""

        self.session = session
        self.documents = PostgresDocumentRepository(session)
        self.runs = PostgresRunRepository(session)
        self.chunks = PostgresChunkRepository(session)
        self.tokens = PostgresTokenRepository(session)
        self.batches = PostgresBatchRepository(session)


class UnitOfWorkFactory:
    """Factory that creates transaction-scoped unit-of-work instances."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Store the SQLAlchemy session factory."""

        self._session_factory = session_factory

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[UnitOfWork]:
        """Yield repositories inside a committed or rolled-back transaction."""

        async with self._session_factory() as session:
            async with session.begin():
                yield UnitOfWork(session)
