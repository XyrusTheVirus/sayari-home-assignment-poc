"""Domain DTOs used across repositories, services, activities, and API views."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from document_pipeline.models.enums import Classification, RunStatus, TokenStatus, WorkStatus


@dataclass(frozen=True, slots=True)
class DocumentRef:
    """Logical document metadata independent from any processing attempt."""

    id: UUID
    external_id: str
    active_run_id: UUID | None


@dataclass(frozen=True, slots=True)
class RunRecord:
    """Versioned processing attempt summary."""

    id: UUID
    document_id: UUID
    version: int
    source_uri: str
    source_checksum: str
    status: RunStatus
    total_chunks: int
    completed_chunks: int
    total_tokens: int | None
    classified_tokens: int
    extraction_started_at: datetime | None
    extraction_completed_at: datetime | None
    classification_started_at: datetime | None
    classification_completed_at: datetime | None
    error_code: str | None
    error_detail: str | None


@dataclass(frozen=True, slots=True)
class ChunkManifest:
    """Deterministic extraction work unit mapped to one bounded object."""

    id: UUID
    run_id: UUID
    chunk_index: int
    object_uri: str
    read_start: int
    read_end: int
    core_start: int
    core_end: int
    status: WorkStatus = WorkStatus.PENDING


@dataclass(frozen=True, slots=True)
class TokenCreate:
    """Token candidate produced by extraction and persisted idempotently."""

    id: UUID
    run_id: UUID
    chunk_id: UUID
    local_index: int
    text: str
    normalized_text_hash: str
    nlp_type: str
    start_offset: int
    end_offset: int
    page_number: int | None
    paragraph_number: int | None
    sentence_number: int | None
    context: str | None


@dataclass(frozen=True, slots=True)
class TokenView:
    """API-safe token projection for listing and classification activities."""

    id: UUID
    text: str
    nlp_type: str
    classification_status: TokenStatus
    classification: Classification | None
    confidence: float | None
    reasoning: str | None
    page_number: int | None
    paragraph_number: int | None
    sentence_number: int | None
    start_offset: int
    end_offset: int
    context: str | None = None


@dataclass(frozen=True, slots=True)
class BatchManifest:
    """Stable bounded classification work assignment for one chunk-local range."""

    id: UUID
    run_id: UUID
    chunk_id: UUID
    start_local_index: int
    end_local_index: int
    status: WorkStatus = WorkStatus.PENDING


@dataclass(frozen=True, slots=True)
class StageProgress:
    """User-facing progress and duration details for one processing stage."""

    completed: int
    total: int | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None


@dataclass(frozen=True, slots=True)
class StatusView:
    """Complete status projection returned by the status endpoint."""

    document_id: str
    run_id: UUID
    active_run_id: UUID | None
    version: int
    status: RunStatus
    extraction: StageProgress
    classification: StageProgress
    error_code: str | None
    error_detail: str | None
