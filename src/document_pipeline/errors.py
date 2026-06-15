"""Domain and infrastructure exceptions translated at application boundaries."""


class PipelineError(Exception):
    """Base class for expected application errors."""

    status_code = 500
    code = "pipeline_error"


class DocumentNotFoundError(PipelineError):
    """Raised when an external document ID cannot be resolved."""

    status_code = 404
    code = "document_not_found"


class RunNotFoundError(PipelineError):
    """Raised when a run ID does not belong to the requested document."""

    status_code = 404
    code = "run_not_found"


class RunConflictError(PipelineError):
    """Raised when a requested run operation conflicts with current state."""

    status_code = 409
    code = "run_conflict"


class InvalidRunStateError(PipelineError):
    """Raised when a guarded state transition is not allowed."""

    status_code = 409
    code = "invalid_run_state"


class ObjectStoreUnavailableError(PipelineError):
    """Raised when MinIO/S3 cannot be reached or returns an unexpected error."""

    status_code = 503
    code = "object_store_unavailable"


class RetryableInfrastructureError(PipelineError):
    """Raised for transient database, object-store, Temporal, or provider errors."""

    status_code = 503
    code = "retryable_infrastructure_error"


class PermanentExtractionError(PipelineError):
    """Raised when extraction cannot continue for deterministic input reasons."""

    status_code = 422
    code = "permanent_extraction_error"


class PermanentClassificationError(PipelineError):
    """Raised when classification receives invalid deterministic token data."""

    status_code = 422
    code = "permanent_classification_error"
