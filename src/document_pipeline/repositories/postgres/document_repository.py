"""PostgreSQL implementation of document repository operations."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from document_pipeline.models.domain import DocumentRef
from document_pipeline.models.orm.document import DocumentORM
from document_pipeline.repositories.postgres.mappers import document_ref


class PostgresDocumentRepository:
    """SQLAlchemy-backed logical document repository."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the transaction-scoped session."""

        self._session = session

    async def get_by_external_id(self, external_id: str) -> DocumentRef | None:
        """Return a document by API-facing external ID."""

        row = await self._session.scalar(select(DocumentORM).where(DocumentORM.external_id == external_id))
        return document_ref(row) if row else None

    async def create_if_absent(self, external_id: str) -> DocumentRef:
        """Insert a document if absent, tolerating concurrent creators."""

        statement = (
            insert(DocumentORM)
            .values(external_id=external_id)
            .on_conflict_do_nothing(index_elements=[DocumentORM.external_id])
        )
        await self._session.execute(statement)
        document = await self.get_by_external_id(external_id)
        if document is None:  # pragma: no cover - defensive database invariant
            raise RuntimeError("document insert/read failed")
        return document

    async def lock_by_id(self, document_id: UUID) -> DocumentRef:
        """Lock a document row while deriving the next run version."""

        row = await self._session.scalar(select(DocumentORM).where(DocumentORM.id == document_id).with_for_update())
        if row is None:
            raise RuntimeError("document disappeared while locking")
        return document_ref(row)

    async def publish_active_run(self, document_id: UUID, run_id: UUID) -> None:
        """Atomically publish a completed run as the active document result."""

        row = await self._session.get(DocumentORM, document_id, with_for_update=True)
        if row is None:
            raise RuntimeError("document missing during active-run publication")
        row.active_run_id = run_id
