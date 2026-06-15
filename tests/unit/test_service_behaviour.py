"""Unit tests for service-level domain behavior with fakes."""

from uuid import UUID

import pytest

from document_pipeline.errors import RunConflictError
from document_pipeline.services.rerun_service import RerunService


class DummyUowFactory:
    """Fake UOW factory unused by validation-only tests."""


class DummyStore:
    """Fake object store unused by validation-only tests."""


class DummyProcessing:
    """Fake processing service unused by validation-only tests."""


@pytest.mark.asyncio
async def test_rerun_rejects_ambiguous_source_choice() -> None:
    """Rerun service enforces full-rerun source invariants before persistence."""

    service = RerunService(DummyUowFactory(), DummyStore(), DummyProcessing())  # type: ignore[arg-type]
    with pytest.raises(RunConflictError):
        await service.rerun("doc-1", text="New", reuse_source=True)


def test_uuid_import_keeps_file_typed() -> None:
    """Keep UUID available for future fake service assertions."""

    assert UUID("00000000-0000-0000-0000-000000000001")
