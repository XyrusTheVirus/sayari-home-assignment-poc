"""Response schemas for processing requests."""

from uuid import UUID

from pydantic import BaseModel

from document_pipeline.models.enums import RunStatus


class ProcessResponse(BaseModel):
    """Accepted processing response."""

    document_id: str
    run_id: UUID
    version: int
    status: RunStatus
    status_url: str
