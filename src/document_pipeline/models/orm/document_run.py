"""ORM model for versioned document processing runs."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from document_pipeline.models.enums import RunStatus
from document_pipeline.models.orm.base import Base, TimestampMixin, enum_values


class DocumentRunORM(TimestampMixin, Base):
    """Version-isolated processing attempt for a logical document."""

    __tablename__ = "document_runs"
    __table_args__ = (
        UniqueConstraint("document_id", "version", name="uq_document_runs_document_id_version"),
        CheckConstraint("total_chunks >= 0", name="total_chunks_non_negative"),
        CheckConstraint("completed_chunks >= 0", name="completed_chunks_non_negative"),
        CheckConstraint("completed_chunks <= total_chunks", name="completed_chunks_lte_total"),
        CheckConstraint("classified_tokens >= 0", name="classified_tokens_non_negative"),
        CheckConstraint(
            "total_tokens IS NULL OR classified_tokens <= total_tokens",
            name="classified_tokens_lte_total_tokens",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_uri: Mapped[str] = mapped_column(Text, nullable=False)
    source_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, values_callable=enum_values, name="run_status"), default=RunStatus.PENDING
    )
    total_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_chunks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    classified_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extraction_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    extraction_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    classification_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    classification_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    extractor_version: Mapped[str] = mapped_column(Text, nullable=False)
    classifier_version: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    document = relationship("DocumentORM", back_populates="runs", foreign_keys=[document_id])
    chunks = relationship("DocumentChunkORM", back_populates="run", cascade="all, delete-orphan")
