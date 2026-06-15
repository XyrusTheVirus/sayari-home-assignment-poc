"""ORM model for extraction chunks."""

from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from document_pipeline.models.enums import WorkStatus
from document_pipeline.models.orm.base import Base, enum_values


class DocumentChunkORM(Base):
    """Durable checkpoint for bounded extraction work."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("run_id", "chunk_index", name="uq_document_chunks_run_id_chunk_index"),
        CheckConstraint("attempts >= 0", name="attempts_non_negative"),
        CheckConstraint("extracted_token_count >= 0", name="extracted_token_count_non_negative"),
        CheckConstraint("read_start <= read_end", name="read_range_valid"),
        CheckConstraint("core_start <= core_end", name="core_range_valid"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    object_uri: Mapped[str] = mapped_column(Text, nullable=False)
    read_start: Mapped[int] = mapped_column(nullable=False)
    read_end: Mapped[int] = mapped_column(nullable=False)
    core_start: Mapped[int] = mapped_column(nullable=False)
    core_end: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[WorkStatus] = mapped_column(
        Enum(WorkStatus, values_callable=enum_values, name="work_status"), default=WorkStatus.PENDING
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extracted_token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at = mapped_column(nullable=True)
    completed_at = mapped_column(nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    run = relationship("DocumentRunORM", back_populates="chunks")
