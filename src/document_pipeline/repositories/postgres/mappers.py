"""Mapping helpers from ORM rows to domain DTOs."""

from document_pipeline.models.domain import (
    BatchManifest,
    ChunkManifest,
    DocumentRef,
    RunRecord,
    TokenView,
)
from document_pipeline.models.orm.classification_batch import ClassificationBatchORM
from document_pipeline.models.orm.document import DocumentORM
from document_pipeline.models.orm.document_chunk import DocumentChunkORM
from document_pipeline.models.orm.document_run import DocumentRunORM
from document_pipeline.models.orm.token import TokenORM


def document_ref(row: DocumentORM) -> DocumentRef:
    """Map a document ORM row to a domain reference."""

    return DocumentRef(id=row.id, external_id=row.external_id, active_run_id=row.active_run_id)


def run_record(row: DocumentRunORM) -> RunRecord:
    """Map a run ORM row to a domain record."""

    return RunRecord(
        id=row.id,
        document_id=row.document_id,
        version=row.version,
        source_uri=row.source_uri,
        source_checksum=row.source_checksum,
        status=row.status,
        total_chunks=row.total_chunks,
        completed_chunks=row.completed_chunks,
        total_tokens=row.total_tokens,
        classified_tokens=row.classified_tokens,
        extraction_started_at=row.extraction_started_at,
        extraction_completed_at=row.extraction_completed_at,
        classification_started_at=row.classification_started_at,
        classification_completed_at=row.classification_completed_at,
        error_code=row.error_code,
        error_detail=row.error_detail,
    )


def chunk_manifest(row: DocumentChunkORM) -> ChunkManifest:
    """Map a chunk ORM row to a domain manifest."""

    return ChunkManifest(
        id=row.id,
        run_id=row.run_id,
        chunk_index=row.chunk_index,
        object_uri=row.object_uri,
        read_start=row.read_start,
        read_end=row.read_end,
        core_start=row.core_start,
        core_end=row.core_end,
        status=row.status,
    )


def token_view(row: TokenORM) -> TokenView:
    """Map a token ORM row to an API/activity-safe projection."""

    return TokenView(
        id=row.id,
        text=row.text,
        nlp_type=row.nlp_type,
        classification_status=row.classification_status,
        classification=row.classification,
        confidence=row.confidence,
        reasoning=row.reasoning,
        page_number=row.page_number,
        paragraph_number=row.paragraph_number,
        sentence_number=row.sentence_number,
        start_offset=row.start_offset,
        end_offset=row.end_offset,
        context=row.context,
    )


def batch_manifest(row: ClassificationBatchORM) -> BatchManifest:
    """Map a batch ORM row to a domain manifest."""

    return BatchManifest(
        id=row.id,
        run_id=row.run_id,
        chunk_id=row.chunk_id,
        start_local_index=row.start_local_index,
        end_local_index=row.end_local_index,
        status=row.status,
    )
