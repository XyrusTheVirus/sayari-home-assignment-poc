"""Repository protocols that keep services independent from SQLAlchemy details."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from document_pipeline.integrations.classifier import ClassificationResult
from document_pipeline.models.domain import (
    BatchManifest,
    ChunkManifest,
    DocumentRef,
    RunRecord,
    TokenCreate,
    TokenView,
)
from document_pipeline.models.enums import Classification, RunStatus, TokenStatus


@dataclass(frozen=True, slots=True)
class TokenFilters:
    """Supported token query filters for API and service-level reads."""

    classification: Classification | None = None
    page_number: int | None = None
    nlp_type: str | None = None
    classification_status: TokenStatus | None = None


@dataclass(frozen=True, slots=True)
class TokenCursor:
    """Decoded keyset cursor ordered by page, start offset, and token ID."""

    page_number: int | None
    start_offset: int
    token_id: UUID


class DocumentRepository(Protocol):
    """Persistence contract for logical documents."""

    async def get_by_external_id(self, external_id: str) -> DocumentRef | None: ...
    async def create_if_absent(self, external_id: str) -> DocumentRef: ...
    async def lock_by_id(self, document_id: UUID) -> DocumentRef: ...
    async def publish_active_run(self, document_id: UUID, run_id: UUID) -> None: ...


class RunRepository(Protocol):
    """Persistence contract for versioned document runs."""

    async def create(
        self,
        document_id: UUID,
        version: int,
        source_uri: str,
        source_checksum: str,
        extractor_version: str,
        classifier_version: str,
        model_version: str | None,
        prompt_version: str | None,
    ) -> RunRecord: ...
    async def get(self, run_id: UUID) -> RunRecord | None: ...
    async def latest_for_document(self, document_id: UUID) -> RunRecord | None: ...
    async def next_version_for_document(self, document_id: UUID) -> int: ...
    async def transition(self, run_id: UUID, expected: RunStatus, target: RunStatus) -> None: ...
    async def mark_extraction_started(self, run_id: UUID, total_chunks: int) -> None: ...
    async def finalize_extraction(self, run_id: UUID, total_tokens: int) -> None: ...
    async def mark_classification_started(self, run_id: UUID) -> None: ...
    async def finalize_completed(self, run_id: UUID) -> None: ...
    async def mark_failed(self, run_id: UUID, code: str, detail: str) -> None: ...


class ChunkRepository(Protocol):
    """Persistence contract for extraction work chunks."""

    async def bulk_create(self, chunks: list[ChunkManifest]) -> None: ...
    async def get(self, chunk_id: UUID) -> ChunkManifest | None: ...
    async def mark_running(self, chunk_id: UUID) -> bool: ...
    async def mark_completed(self, chunk_id: UUID, token_count: int) -> bool: ...
    async def list_by_run(self, run_id: UUID) -> list[ChunkManifest]: ...
    async def incomplete_count(self, run_id: UUID) -> int: ...


class TokenRepository(Protocol):
    """Persistence contract for token candidates and classification results."""

    async def bulk_upsert(self, tokens: list[TokenCreate]) -> int: ...
    async def count_by_run(self, run_id: UUID) -> int: ...
    async def get_unfinished_for_batch(self, batch: BatchManifest) -> list[TokenView]: ...
    async def complete_classification(
        self,
        run_id: UUID,
        token_id: UUID,
        result: ClassificationResult,
        classifier_version: str,
    ) -> bool: ...
    async def query(
        self,
        run_id: UUID,
        filters: TokenFilters,
        limit: int,
        cursor: TokenCursor | None,
    ) -> tuple[list[TokenView], TokenCursor | None]: ...
    async def completed_count(self, run_id: UUID) -> int: ...


class BatchRepository(Protocol):
    """Persistence contract for classification batches."""

    async def bulk_create(self, batches: list[BatchManifest]) -> None: ...
    async def get(self, batch_id: UUID) -> BatchManifest | None: ...
    async def mark_running(self, batch_id: UUID) -> bool: ...
    async def mark_completed(self, batch_id: UUID, processed_count: int) -> bool: ...
    async def list_by_run(self, run_id: UUID) -> list[BatchManifest]: ...
    async def incomplete_count(self, run_id: UUID) -> int: ...
