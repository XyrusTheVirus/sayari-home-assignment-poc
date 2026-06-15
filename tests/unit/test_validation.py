"""Unit tests for API request validation."""

import pytest
from pydantic import ValidationError

from document_pipeline.api.validations.document_requests import RerunRequest
from document_pipeline.api.validations.process_requests import ProcessRequest


def test_process_request_trims_and_accepts_safe_document_id() -> None:
    """Safe external IDs are trimmed and preserved."""

    payload = ProcessRequest(document_id=" doc-123 ", text="John Smith works at Acme Corp.")
    assert payload.document_id == "doc-123"


def test_process_request_rejects_unsafe_document_id() -> None:
    """Unsafe document IDs fail validation before reaching services."""

    with pytest.raises(ValidationError):
        ProcessRequest(document_id="../secret", text="hello")


def test_rerun_requires_exactly_one_source_choice() -> None:
    """Reruns require new text or source reuse, but not both."""

    assert RerunRequest(text="New text", reuse_source=False).text == "New text"
    assert RerunRequest(reuse_source=True).reuse_source is True
    with pytest.raises(ValidationError):
        RerunRequest(text="New text", reuse_source=True)
