"""Enumerations persisted in PostgreSQL and exposed through the API."""

from enum import StrEnum


class RunStatus(StrEnum):
    """Lifecycle state for a versioned document processing run."""

    PENDING = "PENDING"
    EXTRACTING = "EXTRACTING"
    CLASSIFICATION_PENDING = "CLASSIFICATION_PENDING"
    CLASSIFYING = "CLASSIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkStatus(StrEnum):
    """Durable state for chunk and batch work units."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TokenStatus(StrEnum):
    """Durable state for token classification progress."""

    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Classification(StrEnum):
    """Supported final classification labels."""

    COMPANY = "COMPANY"
    PERSON = "PERSON"
    ADDRESS = "ADDRESS"
    DATE = "DATE"
    UNKNOWN = "UNKNOWN"
