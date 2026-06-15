"""Provider-neutral token classification contract."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from document_pipeline.models.enums import Classification


@dataclass(frozen=True, slots=True)
class ClassificationInput:
    """Bounded token data needed by a classifier provider."""

    token_id: UUID
    text: str
    context: str | None
    nlp_type: str


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    """Deterministic classification result persisted to a token."""

    classification: Classification
    confidence: float
    reasoning: str
    model_version: str
    prompt_version: str | None


class Classifier(Protocol):
    """Replaceable LLM/classifier provider interface."""

    version: str

    async def classify(self, value: ClassificationInput) -> ClassificationResult:
        """Classify one token candidate."""
