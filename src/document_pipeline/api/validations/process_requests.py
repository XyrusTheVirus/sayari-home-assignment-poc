"""Request schemas for starting processing."""

from pydantic import BaseModel, field_validator

from document_pipeline.api.validations.common import DOCUMENT_ID_RE


class ProcessRequest(BaseModel):
    """Validated request body for `/process`."""

    document_id: str
    text: str

    @field_validator("document_id")
    @classmethod
    def document_id_is_safe(cls, value: str) -> str:
        """Trim and validate safe slug-like document IDs."""

        trimmed = value.strip()
        if not DOCUMENT_ID_RE.fullmatch(trimmed):
            raise ValueError("document_id must be 1-128 safe slug characters")
        return trimmed

    @field_validator("text")
    @classmethod
    def text_is_non_empty(cls, value: str) -> str:
        """Reject empty or control-only source text."""

        if not value.strip() or not any(not character.isspace() and character.isprintable() for character in value):
            raise ValueError("text must contain printable content")
        return value
