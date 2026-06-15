"""Provider-neutral extraction contract."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class ExtractionInput:
    """Bounded source text plus global offset metadata for extraction."""

    text: str
    base_offset: int
    page_base: int = 1


@dataclass(frozen=True, slots=True)
class ExtractedEntity:
    """Entity candidate returned by an extractor provider."""

    text: str
    nlp_type: str
    start_offset: int
    end_offset: int
    page_number: int | None
    paragraph_number: int | None
    sentence_number: int | None
    context: str


class Extractor(Protocol):
    """Replaceable NLP extraction provider interface."""

    version: str

    async def extract(self, value: ExtractionInput) -> Sequence[ExtractedEntity]:
        """Extract entity candidates from bounded text."""
