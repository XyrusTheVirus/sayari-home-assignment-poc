"""Request/query schemas for document operations."""

from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from document_pipeline.models.enums import Classification, TokenStatus


class RerunRequest(BaseModel):
    """Validated request body for creating a full rerun."""

    text: str | None = None
    reuse_source: bool = False

    @model_validator(mode="after")
    def exactly_one_source(self) -> "RerunRequest":
        """Require either new text or reuse_source=true, but not both."""

        has_text = self.text is not None and bool(self.text.strip())
        if has_text == self.reuse_source:
            raise ValueError("provide exactly one of non-empty text or reuse_source=true")
        return self


class TokenQueryParams(BaseModel):
    """Supported token filters and pagination query parameters."""

    classification: Classification | None = None
    page_number: int | None = Field(default=None, ge=1)
    nlp_type: str | None = None
    classification_status: TokenStatus | None = None
    run_id: UUID | None = None
    limit: int = Field(default=50, ge=1, le=200)
    cursor: str | None = None
