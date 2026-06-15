"""Shared API validation helpers and response models."""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DOCUMENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class ProblemDetails(BaseModel):
    """Consistent client-safe error response."""

    error: str
    detail: str
    request_id: str | None = None


class StageProgressResponse(BaseModel):
    """API representation of stage progress and finalized duration."""

    completed_chunks: int | None = None
    total_chunks: int | None = None
    processed_count: int | None = None
    total_tokens: int | None = None
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None


class TokenItemResponse(BaseModel):
    """API representation of one token result."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    text: str
    nlp_type: str
    classification: str | None
    confidence: float | None
    reasoning: str | None
    page_number: int | None
    paragraph_number: int | None
    sentence_number: int | None
    start_offset: int
    end_offset: int


class PaginationParams(BaseModel):
    """Validated pagination parameters."""

    limit: int = Field(default=50, ge=1, le=200)
    cursor: str | None = None
