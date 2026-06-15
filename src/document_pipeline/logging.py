"""Structured JSON logging with request and workflow correlation fields."""

import logging
import sys
from contextvars import ContextVar
from typing import Any

from pythonjsonlogger.json import JsonFormatter

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


class CorrelationFilter(logging.Filter):
    """Inject context-local correlation values into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Attach the active request ID when one exists."""

        record.request_id = request_id_var.get()
        return True


def configure_logging(level: str) -> None:
    """Configure root logging once for API and worker processes."""

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s "
            "%(document_id)s %(run_id)s %(workflow_id)s %(chunk_id)s %(batch_id)s %(token_id)s"
        )
    )
    handler.addFilter(CorrelationFilter())
    logging.basicConfig(level=level.upper(), handlers=[handler], force=True)


def extra(**values: Any) -> dict[str, Any]:
    """Build a logging `extra` dictionary with common correlation keys."""

    return {"extra": values}
