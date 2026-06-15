"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create document processing schema, constraints, and indexes."""

    run_status = postgresql.ENUM(
        "PENDING",
        "EXTRACTING",
        "CLASSIFICATION_PENDING",
        "CLASSIFYING",
        "COMPLETED",
        "FAILED",
        "CANCELLED",
        name="run_status",
    )
    work_status = postgresql.ENUM("PENDING", "RUNNING", "COMPLETED", "FAILED", name="work_status")
    token_status = postgresql.ENUM("PENDING", "COMPLETED", "FAILED", name="token_status")
    classification = postgresql.ENUM("COMPANY", "PERSON", "ADDRESS", "DATE", "UNKNOWN", name="classification")
    bind = op.get_bind()
    run_status.create(bind, checkfirst=True)
    work_status.create(bind, checkfirst=True)
    token_status.create(bind, checkfirst=True)
    classification.create(bind, checkfirst=True)

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("active_run_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("external_id", name="uq_documents_external_id"),
    )
    op.create_index("ix_documents_external_id", "documents", ["external_id"])

    op.create_table(
        "document_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=False),
        sa.Column("source_checksum", sa.String(length=64), nullable=False),
        sa.Column("status", run_status, nullable=False),
        sa.Column("total_chunks", sa.Integer(), nullable=False),
        sa.Column("completed_chunks", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("classified_tokens", sa.Integer(), nullable=False),
        sa.Column("extraction_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extraction_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("classification_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("classification_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extractor_version", sa.Text(), nullable=False),
        sa.Column("classifier_version", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.Text(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("total_chunks >= 0", name="ck_document_runs_total_chunks_non_negative"),
        sa.CheckConstraint("completed_chunks >= 0", name="ck_document_runs_completed_chunks_non_negative"),
        sa.CheckConstraint("completed_chunks <= total_chunks", name="ck_document_runs_completed_chunks_lte_total"),
        sa.CheckConstraint("classified_tokens >= 0", name="ck_document_runs_classified_tokens_non_negative"),
        sa.CheckConstraint(
            "total_tokens IS NULL OR classified_tokens <= total_tokens",
            name="ck_document_runs_classified_tokens_lte_total_tokens",
        ),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("document_id", "version", name="uq_document_runs_document_id_version"),
    )
    op.create_index("ix_document_runs_document_id", "document_runs", ["document_id"])
    op.create_foreign_key("fk_documents_active_run_id_document_runs", "documents", "document_runs", ["active_run_id"], ["id"])

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("object_uri", sa.Text(), nullable=False),
        sa.Column("read_start", sa.BigInteger(), nullable=False),
        sa.Column("read_end", sa.BigInteger(), nullable=False),
        sa.Column("core_start", sa.BigInteger(), nullable=False),
        sa.Column("core_end", sa.BigInteger(), nullable=False),
        sa.Column("status", work_status, nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("extracted_token_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.CheckConstraint("attempts >= 0", name="ck_document_chunks_attempts_non_negative"),
        sa.CheckConstraint("extracted_token_count >= 0", name="ck_document_chunks_extracted_token_count_non_negative"),
        sa.CheckConstraint("read_start <= read_end", name="ck_document_chunks_read_range_valid"),
        sa.CheckConstraint("core_start <= core_end", name="ck_document_chunks_core_range_valid"),
        sa.ForeignKeyConstraint(["run_id"], ["document_runs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("run_id", "chunk_index", name="uq_document_chunks_run_id_chunk_index"),
    )
    op.create_index("ix_document_chunks_run_id", "document_chunks", ["run_id"])

    op.create_table(
        "tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("local_index", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("normalized_text_hash", sa.String(length=64), nullable=False),
        sa.Column("nlp_type", sa.Text(), nullable=False),
        sa.Column("start_offset", sa.BigInteger(), nullable=False),
        sa.Column("end_offset", sa.BigInteger(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("paragraph_number", sa.Integer(), nullable=True),
        sa.Column("sentence_number", sa.Integer(), nullable=True),
        sa.Column("context", sa.Text(), nullable=True),
        sa.Column("classification_status", token_status, nullable=False),
        sa.Column("classification", classification, nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("classifier_version", sa.Text(), nullable=True),
        sa.Column("model_version", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.Text(), nullable=True),
        sa.Column("classified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("start_offset <= end_offset", name="ck_tokens_token_offsets_valid"),
        sa.CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_tokens_confidence_valid"),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["document_runs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("run_id", "start_offset", "end_offset", "normalized_text_hash", name="uq_tokens_run_span_hash"),
    )
    op.create_index("ix_tokens_run_id", "tokens", ["run_id"])
    op.create_index("ix_tokens_chunk_id", "tokens", ["chunk_id"])
    op.create_index("ix_tokens_run_page", "tokens", ["run_id", "page_number", "start_offset", "id"])
    op.create_index("ix_tokens_run_classification", "tokens", ["run_id", "classification", "id"])
    op.create_index(
        "ix_tokens_pending",
        "tokens",
        ["run_id", "chunk_id", "local_index"],
        postgresql_where=sa.text("classification_status = 'PENDING'"),
    )

    op.create_table(
        "classification_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chunk_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_local_index", sa.Integer(), nullable=False),
        sa.Column("end_local_index", sa.Integer(), nullable=False),
        sa.Column("status", work_status, nullable=False),
        sa.Column("processed_count", sa.Integer(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.CheckConstraint("start_local_index <= end_local_index", name="ck_classification_batches_batch_range_valid"),
        sa.CheckConstraint("processed_count >= 0", name="ck_classification_batches_processed_count_non_negative"),
        sa.CheckConstraint("attempts >= 0", name="ck_classification_batches_batch_attempts_non_negative"),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["run_id"], ["document_runs.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("run_id", "chunk_id", "start_local_index", "end_local_index", name="uq_classification_batches_range"),
    )
    op.create_index("ix_classification_batches_run_id", "classification_batches", ["run_id"])
    op.create_index("ix_classification_batches_chunk_id", "classification_batches", ["chunk_id"])


def downgrade() -> None:
    """Drop schema objects in reverse dependency order."""

    op.drop_table("classification_batches")
    op.drop_table("tokens")
    op.drop_table("document_chunks")
    op.drop_constraint("fk_documents_active_run_id_document_runs", "documents", type_="foreignkey")
    op.drop_table("document_runs")
    op.drop_table("documents")
    for name in ("classification", "token_status", "work_status", "run_status"):
        postgresql.ENUM(name=name).drop(op.get_bind(), checkfirst=True)
