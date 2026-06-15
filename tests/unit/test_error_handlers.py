"""Unit tests for API error response formatting."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from document_pipeline.api.exception_handlers import (
    ErrorHandlerConfig,
    build_error_response,
    register_error_handler,
)


class DemoCustomError(Exception):
    """Custom exception used to verify extensible error registration."""


def test_build_error_response_includes_status_code_and_message() -> None:
    """The public error envelope contains review-friendly error fields."""

    response = build_error_response(status_code=409, code="conflict", message="Run conflict.")
    assert response.status_code == 409
    assert response.body
    assert b'"status_code":409' in response.body
    assert b'"message":"Run conflict."' in response.body


def test_register_error_handler_supports_custom_errors() -> None:
    """Custom exception types can be registered without changing core handlers."""

    app = FastAPI()
    register_error_handler(
        app,
        DemoCustomError,
        ErrorHandlerConfig(status_code=418, code="demo_error", message="Demo failed."),
    )

    @app.get("/demo")
    async def demo() -> None:
        raise DemoCustomError

    response = TestClient(app).get("/demo")
    assert response.status_code == 418
    assert response.json()["error"]["code"] == "demo_error"
    assert response.json()["error"]["message"] == "Demo failed."
