"""ORM model for extracted token candidates and classification results."""

from uuid import UUID

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from document_pipeline.models.enums import Classification, TokenStatus
from document_pipeline.models.orm.base import Base, TimestampMixin, enum_values


class TokenORM(TimestampMixin, Base):
    """Entity candidate token with idempotent classification state."""

    __tablename__ = "tokens"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "start_offset",
            "end_offset",
            "normalized_text_hash",
            name="uq_tokens_run_span_hash",
        ),
        CheckConstraint("start_offset <= end_offset", name="token_offsets_valid"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="confidence_valid"),
        Index("ix_tokens_run_page", "run_id", "page_number", "start_offset", "id"),
        Index("ix_tokens_run_classification", "run_id", "classification", "id"),
        Index(
            "ix_tokens_pending",
            "run_id",
            "chunk_id",
            "local_index",
            postgresql_where="classification_status = 'PENDING'",
        ),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True)
    run_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    local_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    nlp_type: Mapped[str] = mapped_column(Text, nullable=False)
    start_offset: Mapped[int] = mapped_column(nullable=False)
    end_offset: Mapped[int] = mapped_column(nullable=False)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paragraph_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sentence_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification_status: Mapped[TokenStatus] = mapped_column(
        Enum(TokenStatus, values_callable=enum_values, name="token_status"), default=TokenStatus.PENDING
    )
    classification: Mapped[Classification | None] = mapped_column(
        Enum(Classification, values_callable=enum_values, name="classification"), nullable=True
    )
    confidence: Mapped[float | None] = mapped_column(nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    classifier_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    classified_at = mapped_column(nullable=True)
