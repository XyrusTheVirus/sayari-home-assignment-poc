"""Compose-backed API integration tests for the document pipeline."""

import asyncio
import os
import subprocess
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_COMPOSE_INTEGRATION") != "1",
    reason="requires the Docker Compose stack and RUN_COMPOSE_INTEGRATION=1",
)

BASE_URL = os.getenv("INTEGRATION_BASE_URL", "http://localhost:8080")
ROOT = Path(__file__).resolve().parents[2]
DEADLINE_SECONDS = float(os.getenv("INTEGRATION_DEADLINE_SECONDS", "180"))


class ApiHarness:
    """Small HTTP client wrapper with polling and diagnostics for integration tests."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        """Store the HTTPX client used by all API requests."""

        self._client = client

    async def submit(self, document_id: str, text: str) -> dict[str, Any]:
        """Submit a document for asynchronous processing."""

        response = await self._request(
            "POST",
            "/process",
            json={"document_id": document_id, "text": text},
        )
        assert response.status_code == 202, response.text
        return response.json()

    async def rerun(
        self, document_id: str, text: str | None = None, reuse_source: bool = False
    ) -> dict[str, Any]:
        """Start a full rerun with new text or reused source."""

        response = await self._request(
            "POST",
            f"/api/v1/documents/{document_id}/rerun",
            json={"text": text, "reuse_source": reuse_source},
        )
        assert response.status_code == 202, response.text
        return response.json()

    async def status(self, document_id: str, run_id: str | None = None) -> dict[str, Any]:
        """Fetch document status for the latest or specific run."""

        response = await self._request(
            "GET",
            f"/documents/{document_id}/status",
            params={"run_id": run_id} if run_id else None,
        )
        assert response.status_code == 200, response.text
        return response.json()

    async def tokens(self, document_id: str, **params: Any) -> dict[str, Any]:
        """Query tokens for a document with optional filters."""

        response = await self._request("GET", f"/documents/{document_id}/tokens", params=params)
        assert response.status_code == 200, response.text
        return response.json()

    async def ready(self) -> dict[str, Any]:
        """Fetch readiness with the same retry behavior as workflow requests."""

        response = await self._request("GET", "/health/ready")
        assert response.status_code == 200, response.text
        return response.json()

    async def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Send an HTTP request, retrying transient Docker port disruptions."""

        last_error: Exception | None = None
        for _attempt in range(20):
            try:
                return await self._client.request(method, path, **kwargs)
            except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadTimeout) as exc:
                last_error = exc
                await asyncio.sleep(0.5)
        raise AssertionError(f"API request failed after retries: {method} {path}") from last_error

    async def wait_for_completion(
        self, document_id: str, run_id: str | None = None
    ) -> dict[str, Any]:
        """Poll until a run completes or fail with the last status payload."""

        last_status: dict[str, Any] | None = None
        deadline = time.monotonic() + DEADLINE_SECONDS
        while time.monotonic() < deadline:
            last_status = await self.status(document_id, run_id)
            if last_status["status"] == "COMPLETED":
                return last_status
            if last_status["status"] in {"FAILED", "CANCELLED"}:
                pytest.fail(f"run reached terminal failure: {last_status}")
            await asyncio.sleep(1)
        pytest.fail(f"timed out waiting for completion; last_status={last_status}")

    async def wait_for_classification_progress(self, document_id: str) -> dict[str, Any]:
        """Poll until classification has made partial progress."""

        last_status: dict[str, Any] | None = None
        deadline = time.monotonic() + DEADLINE_SECONDS
        while time.monotonic() < deadline:
            last_status = await self.status(document_id)
            classification = last_status["classification"]
            processed = classification["processed_count"] or 0
            total = classification["total_tokens"] or 0
            if last_status["status"] == "CLASSIFYING" and 0 < processed < total:
                return last_status
            if last_status["status"] in {"FAILED", "CANCELLED"}:
                pytest.fail(f"run reached terminal failure: {last_status}")
            await asyncio.sleep(0.5)
        pytest.fail(
            f"timed out waiting for partial classification progress; last_status={last_status}"
        )


@pytest.fixture
async def api() -> ApiHarness:
    """Create an HTTPX client for the running API service."""

    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=20,
        limits=httpx.Limits(max_keepalive_connections=0),
    ) as client:
        yield ApiHarness(client)


def unique_document_id(prefix: str) -> str:
    """Return a safe unique external document ID."""

    return f"it-{prefix}-{uuid4().hex[:12]}"


def document_text(name: str) -> str:
    """Read a test document by filename from the repository fixtures."""

    return (ROOT / "test_documents" / name).read_text(encoding="utf-8")


def compose(*args: str) -> None:
    """Run a Docker Compose command for worker recovery scenarios."""

    completed = subprocess.run(
        ["docker", "compose", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout


@pytest.mark.asyncio
async def test_health_ready_contract(api: ApiHarness) -> None:
    """Verify the API readiness endpoint against a running local stack."""

    assert (await api.ready())["status"] == "ready"


@pytest.mark.asyncio
async def test_happy_path_small_document(api: ApiHarness) -> None:
    """Submit a small document, wait for completion, and assert classified tokens."""

    document_id = unique_document_id("happy")
    accepted = await api.submit(document_id, document_text("small.txt"))
    status = await api.wait_for_completion(document_id, accepted["run_id"])
    assert status["active_run_id"] == accepted["run_id"]
    assert status["extraction"]["duration_ms"] is not None
    assert status["processed_tokens"] == status["classification"]["processed_count"]
    assert status["classification"]["processed_count"] == status["classification"]["total_tokens"]

    people = await api.tokens(document_id, classification="PERSON")
    assert people["items"], people
    assert any(item["classification"] == "PERSON" for item in people["items"])


@pytest.mark.asyncio
async def test_progress_visibility_for_large_document(api: ApiHarness) -> None:
    """Observe an intermediate CLASSIFYING response for a large document."""

    document_id = unique_document_id("progress")
    await api.submit(document_id, document_text("large.txt"))
    progress = await api.wait_for_classification_progress(document_id)
    processed = progress["classification"]["processed_count"]
    total = progress["classification"]["total_tokens"]
    assert progress["processed_tokens"] == processed
    assert 0 < processed < total
    await api.wait_for_completion(document_id, progress["run_id"])


@pytest.mark.asyncio
async def test_partial_classification_recovery(api: ApiHarness) -> None:
    """Stop the classification worker mid-run and verify progress resumes."""

    document_id = unique_document_id("recovery")
    await api.submit(document_id, document_text("large.txt"))
    progress = await api.wait_for_classification_progress(document_id)
    before_stop = progress["classification"]["processed_count"]
    total = progress["classification"]["total_tokens"]
    assert before_stop < total

    compose("stop", "classification-worker")
    try:
        stopped_status = await api.status(document_id)
        persisted = stopped_status["classification"]["processed_count"]
        assert persisted >= before_stop
    finally:
        compose("start", "classification-worker")

    completed = await api.wait_for_completion(document_id, progress["run_id"])
    assert (
        completed["classification"]["processed_count"]
        == completed["classification"]["total_tokens"]
    )


@pytest.mark.asyncio
async def test_full_rerun_preserves_old_active_result_until_publication(api: ApiHarness) -> None:
    """Verify full rerun isolation and active-run pointer publication semantics."""

    document_id = unique_document_id("rerun")
    first = await api.submit(document_id, document_text("small.txt"))
    first_status = await api.wait_for_completion(document_id, first["run_id"])
    first_active_run_id = first_status["active_run_id"]
    first_people = await api.tokens(document_id, classification="PERSON")

    rerun_text = (
        document_text("medium.txt")
        + "\nElena Park joined Contoso LLC at 800 Pine Street on 2026-06-15."
    )
    second = await api.rerun(document_id, text=rerun_text)
    during = await api.status(document_id)
    assert during["active_run_id"] == first_active_run_id
    assert second["run_id"] != first["run_id"]

    completed = await api.wait_for_completion(document_id, second["run_id"])
    assert completed["active_run_id"] == second["run_id"]
    second_people = await api.tokens(document_id, classification="PERSON")
    assert second_people["items"]
    assert second_people["items"] != first_people["items"]


@pytest.mark.asyncio
async def test_concurrent_documents_complete_independently(api: ApiHarness) -> None:
    """Submit small, medium, and large documents concurrently and wait for all."""

    documents = [
        (unique_document_id("small"), "small.txt"),
        (unique_document_id("medium"), "medium.txt"),
        (unique_document_id("large"), "large.txt"),
    ]
    accepted = await asyncio.gather(
        *(api.submit(document_id, document_text(filename)) for document_id, filename in documents)
    )
    completed = await asyncio.gather(
        *(
            api.wait_for_completion(document_id, result["run_id"])
            for (document_id, _filename), result in zip(documents, accepted, strict=True)
        )
    )
    assert {status["status"] for status in completed} == {"COMPLETED"}


@pytest.mark.asyncio
async def test_token_query_filters(api: ApiHarness) -> None:
    """Filter tokens by classification, page, NLP type, and classification status."""

    document_id = unique_document_id("filters")
    accepted = await api.submit(document_id, document_text("medium.txt"))
    await api.wait_for_completion(document_id, accepted["run_id"])

    people = await api.tokens(document_id, classification="PERSON", limit=10)
    assert people["items"]
    assert all(item["classification"] == "PERSON" for item in people["items"])

    page_two = await api.tokens(document_id, page_number=2, limit=10)
    assert page_two["items"]
    assert all(item["page_number"] == 2 for item in page_two["items"])

    orgs = await api.tokens(document_id, nlp_type="ORG", classification_status="COMPLETED")
    assert orgs["items"]
    assert all(item["nlp_type"] == "ORG" for item in orgs["items"])
