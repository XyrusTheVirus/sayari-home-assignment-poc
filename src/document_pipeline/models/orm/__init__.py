"""Import all ORM models so Alembic can discover metadata."""

from document_pipeline.models.orm.base import Base
from document_pipeline.models.orm.classification_batch import ClassificationBatchORM
from document_pipeline.models.orm.document import DocumentORM
from document_pipeline.models.orm.document_chunk import DocumentChunkORM
from document_pipeline.models.orm.document_run import DocumentRunORM
from document_pipeline.models.orm.token import TokenORM

__all__ = [
    "Base",
    "ClassificationBatchORM",
    "DocumentChunkORM",
    "DocumentORM",
    "DocumentRunORM",
    "TokenORM",
]
