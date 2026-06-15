"""Unit tests for cursor and progress helpers."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from document_pipeline.models.domain import RunRecord
from document_pipeline.models.enums import RunStatus
from document_pipeline.repositories.interfaces import TokenCursor
from document_pipeline.services.cursor import decode_cursor, encode_cursor
from document_pipeline.services.progress_service import ProgressService


def test_cursor_round_trip() -> None:
    """Opaque token cursors round-trip without losing ordering fields."""

    cursor = TokenCursor(None, 42, UUID("00000000-0000-0000-0000-000000000042"))
    assert decode_cursor(encode_cursor(cursor)) == cursor


def test_duration_calculation() -> None:
    """Progress service reports finalized wall-clock duration in milliseconds."""

    started = datetime(2026, 6, 15, tzinfo=UTC)
    completed = started + timedelta(seconds=5)
    run = RunRecord(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        document_id=UUID("00000000-0000-0000-0000-000000000002"),
        version=1,
        source_uri="s3://bucket/key",
        source_checksum="x" * 64,
        status=RunStatus.COMPLETED,
        total_chunks=2,
        completed_chunks=2,
        total_tokens=10,
        classified_tokens=10,
        extraction_started_at=started,
        extraction_completed_at=completed,
        classification_started_at=started,
        classification_completed_at=completed,
        error_code=None,
        error_detail=None,
    )
    assert ProgressService().extraction_progress(run).duration_ms == 5000
