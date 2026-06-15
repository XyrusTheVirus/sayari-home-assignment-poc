"""Unit tests for deterministic chunking."""

from uuid import UUID

import pytest

from document_pipeline.services.chunking_service import ChunkingService, deterministic_uuid, normalized_hash


def test_chunking_produces_non_overlapping_core_ranges_with_overlap() -> None:
    """Chunk core ranges cover the document once while read ranges may overlap."""

    text = "Alpha paragraph.\n\n" * 40
    chunks = ChunkingService(target_chars=120, overlap_chars=20).slice_text(text)
    assert len(chunks) > 1
    assert chunks[0].core_start == 0
    assert chunks[-1].core_end == len(text)
    for previous, current in zip(chunks, chunks[1:], strict=False):
        assert previous.core_end == current.core_start
        assert current.read_start <= current.core_start


def test_token_helpers_are_stable() -> None:
    """Retry IDs and normalized hashes are deterministic."""

    namespace = UUID("00000000-0000-0000-0000-000000000001")
    assert deterministic_uuid(namespace, "x") == deterministic_uuid(namespace, "x")
    assert normalized_hash(" Acme   Corp ") == normalized_hash("acme corp")


def test_invalid_overlap_rejected_by_settings() -> None:
    """Settings validator rejects overlap that prevents chunk progress."""

    from document_pipeline.config import Settings

    with pytest.raises(ValueError):
        Settings(chunk_target_chars=1000, chunk_overlap_chars=1000)
