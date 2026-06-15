"""PostgreSQL implementation of token persistence and queries."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from document_pipeline.integrations.classifier import ClassificationResult
from document_pipeline.models.domain import BatchManifest, TokenCreate, TokenView
from document_pipeline.models.enums import TokenStatus
from document_pipeline.models.orm.document_run import DocumentRunORM
from document_pipeline.models.orm.token import TokenORM
from document_pipeline.repositories.interfaces import TokenCursor, TokenFilters
from document_pipeline.repositories.postgres.mappers import token_view


class PostgresTokenRepository:
    """SQLAlchemy-backed token repository."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the transaction-scoped session."""

        self._session = session

    async def bulk_upsert(self, tokens: list[TokenCreate]) -> int:
        """Insert extracted tokens idempotently and return attempted row count."""

        if not tokens:
            return 0
        statement = insert(TokenORM).values(
            [
                {
                    "id": item.id,
                    "run_id": item.run_id,
                    "chunk_id": item.chunk_id,
                    "local_index": item.local_index,
                    "text": item.text,
                    "normalized_text_hash": item.normalized_text_hash,
                    "nlp_type": item.nlp_type,
                    "start_offset": item.start_offset,
                    "end_offset": item.end_offset,
                    "page_number": item.page_number,
                    "paragraph_number": item.paragraph_number,
                    "sentence_number": item.sentence_number,
                    "context": item.context,
                    "classification_status": TokenStatus.PENDING,
                }
                for item in tokens
            ]
        ).on_conflict_do_nothing(index_elements=["run_id", "start_offset", "end_offset", "normalized_text_hash"])
        await self._session.execute(statement)
        return len(tokens)

    async def count_by_run(self, run_id: UUID) -> int:
        """Count all extracted tokens for a run."""

        value = await self._session.scalar(select(func.count()).select_from(TokenORM).where(TokenORM.run_id == run_id))
        return int(value or 0)

    async def completed_count(self, run_id: UUID) -> int:
        """Count durably completed token classifications for a run."""

        value = await self._session.scalar(
            select(func.count())
            .select_from(TokenORM)
            .where(TokenORM.run_id == run_id, TokenORM.classification_status == TokenStatus.COMPLETED)
        )
        return int(value or 0)

    async def get_unfinished_for_batch(self, batch: BatchManifest) -> list[TokenView]:
        """Load pending tokens assigned to a stable classification batch."""

        rows = (
            await self._session.scalars(
                select(TokenORM)
                .where(
                    TokenORM.run_id == batch.run_id,
                    TokenORM.chunk_id == batch.chunk_id,
                    TokenORM.local_index >= batch.start_local_index,
                    TokenORM.local_index <= batch.end_local_index,
                    TokenORM.classification_status != TokenStatus.COMPLETED,
                )
                .order_by(TokenORM.local_index)
            )
        ).all()
        return [token_view(row) for row in rows]

    async def complete_classification(
        self,
        run_id: UUID,
        token_id: UUID,
        result: ClassificationResult,
        classifier_version: str,
    ) -> bool:
        """Persist one classification and increment progress only on state transition."""

        token = await self._session.get(TokenORM, token_id, with_for_update=True)
        if token is None or token.classification_status == TokenStatus.COMPLETED:
            return False
        now = datetime.now(UTC)
        token.classification_status = TokenStatus.COMPLETED
        token.classification = result.classification
        token.confidence = result.confidence
        token.reasoning = result.reasoning
        token.classifier_version = classifier_version
        token.model_version = result.model_version
        token.prompt_version = result.prompt_version
        token.classified_at = now
        token.updated_at = now
        run = await self._session.get(DocumentRunORM, run_id, with_for_update=True)
        if run is not None:
            run.classified_tokens += 1
            run.updated_at = now
        return True

    async def query(
        self,
        run_id: UUID,
        filters: TokenFilters,
        limit: int,
        cursor: TokenCursor | None,
    ) -> tuple[list[TokenView], TokenCursor | None]:
        """Query tokens with indexed filters and keyset pagination."""

        statement = select(TokenORM).where(TokenORM.run_id == run_id)
        statement = self._apply_filters(statement, filters)
        if cursor is not None:
            page_value = cursor.page_number if cursor.page_number is not None else 2_147_483_647
            current_page = func.coalesce(TokenORM.page_number, 2_147_483_647)
            statement = statement.where(
                or_(
                    current_page > page_value,
                    and_(current_page == page_value, TokenORM.start_offset > cursor.start_offset),
                    and_(
                        current_page == page_value,
                        TokenORM.start_offset == cursor.start_offset,
                        TokenORM.id > cursor.token_id,
                    ),
                )
            )
        rows = (
            await self._session.scalars(
                statement.order_by(
                    func.coalesce(TokenORM.page_number, 2_147_483_647),
                    TokenORM.start_offset,
                    TokenORM.id,
                ).limit(limit + 1)
            )
        ).all()
        page = [token_view(row) for row in rows[:limit]]
        next_cursor = None
        if len(rows) > limit and page:
            last = page[-1]
            next_cursor = TokenCursor(last.page_number, last.start_offset, last.id)
        return page, next_cursor

    def _apply_filters(self, statement: Select[tuple[TokenORM]], filters: TokenFilters) -> Select[tuple[TokenORM]]:
        """Apply optional filters without changing the deterministic ordering."""

        if filters.classification is not None:
            statement = statement.where(TokenORM.classification == filters.classification)
        if filters.page_number is not None:
            statement = statement.where(TokenORM.page_number == filters.page_number)
        if filters.nlp_type is not None:
            statement = statement.where(TokenORM.nlp_type == filters.nlp_type)
        if filters.classification_status is not None:
            statement = statement.where(TokenORM.classification_status == filters.classification_status)
        return statement
