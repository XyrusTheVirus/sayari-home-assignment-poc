"""ORM model for stable classification batches."""

from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from document_pipeline.models.enums import WorkStatus
from document_pipeline.models.orm.base import Base, enum_values


class ClassificationBatchORM(Base):
    """Durable bounded assignment for classifying chunk-local token ranges."""

    __tablename__ = "classification_batches"
    __table_args__ = (
        UniqueConstraint(
            "run_id",
            "chunk_id",
            "start_local_index",
            "end_local_index",
            name="uq_classification_batches_range",
        ),
        CheckConstraint("start_local_index <= end_local_index", name="batch_range_valid"),
        CheckConstraint("processed_count >= 0", name="processed_count_non_negative"),
        CheckConstraint("attempts >= 0", name="batch_attempts_non_negative"),
    )

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("document_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    start_local_index: Mapped[int] = mapped_column(Integer, nullable=False)
    end_local_index: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[WorkStatus] = mapped_column(
        Enum(WorkStatus, values_callable=enum_values, name="work_status"), default=WorkStatus.PENDING
    )
    processed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at = mapped_column(nullable=True)
    completed_at = mapped_column(nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
