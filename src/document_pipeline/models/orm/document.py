"""ORM model for logical documents."""

from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from document_pipeline.models.orm.base import Base, TimestampMixin


class DocumentORM(TimestampMixin, Base):
    """Logical document whose active result points at a completed run."""

    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    external_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    active_run_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("document_runs.id", use_alter=True), nullable=True
    )

    runs = relationship(
        "DocumentRunORM",
        back_populates="document",
        foreign_keys="DocumentRunORM.document_id",
        cascade="all, delete-orphan",
    )
    active_run = relationship("DocumentRunORM", foreign_keys=[active_run_id], post_update=True)
