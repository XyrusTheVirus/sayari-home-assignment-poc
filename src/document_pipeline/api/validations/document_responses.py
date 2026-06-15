"""Response schemas for document status and token queries."""

from uuid import UUID

from pydantic import BaseModel

from document_pipeline.api.validations.common import StageProgressResponse, TokenItemResponse
from document_pipeline.models.enums import RunStatus


class StatusErrorResponse(BaseModel):
    """Failure details for a failed run."""

    code: str
    detail: str | None


class DocumentStatusResponse(BaseModel):
    """Status response for latest, active, or specific run."""

    document_id: str
    run_id: UUID
    active_run_id: UUID | None
    version: int
    status: RunStatus
    extraction: StageProgressResponse
    classification: StageProgressResponse
    error: StatusErrorResponse | None


class TokenListResponse(BaseModel):
    """Paginated token query response."""

    items: list[TokenItemResponse]
    next_cursor: str | None
