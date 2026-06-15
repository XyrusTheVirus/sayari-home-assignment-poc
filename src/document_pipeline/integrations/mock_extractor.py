"""Deterministic rule-based entity extractor for local POC execution."""

import asyncio
import re
from collections.abc import Iterable

from document_pipeline.integrations.extractor import ExtractedEntity, ExtractionInput

ENTITY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "ADDRESS",
        re.compile(
            r"\b\d{1,6}\s+[A-Z][A-Za-z0-9.'-]*(?:\s+[A-Z][A-Za-z0-9.'-]*){0,4}\s+(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Lane|Ln|Drive|Dr|Way|Court|Ct)\b"
        ),
    ),
    (
        "DATE",
        re.compile(
            r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},\s+\d{4}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b"
        ),
    ),
    (
        "ORG",
        re.compile(
            r"\b[A-Z][A-Za-z&.'-]*(?:\s+[A-Z][A-Za-z&.'-]*){0,4}\s+(?:Corp|Corporation|Inc|Ltd|LLC|Group|Technologies|Bank|Partners|Systems)\b"
        ),
    ),
    ("PERSON", re.compile(r"\b(?:Dr\.|Ms\.|Mr\.)?\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b")),
    (
        "GPE",
        re.compile(
            r"\b(?:New York|London|Paris|Berlin|Tel Aviv|San Francisco|Chicago|"
            r"Boston|Austin|Seattle)\b"
        ),
    ),
)


class MockExtractor:
    """Rule-based extractor with deterministic offsets, context, and metadata."""

    version = "mock-extractor-v1"

    def __init__(self, delay_ms: int = 0, context_chars: int = 80) -> None:
        """Configure optional artificial latency and context window size."""

        self._delay_ms = delay_ms
        self._context_chars = context_chars

    async def extract(self, value: ExtractionInput) -> list[ExtractedEntity]:
        """Return sorted, non-overlapping entities detected by regex rules."""

        if self._delay_ms:
            await asyncio.sleep(self._delay_ms / 1_000)
        candidates = list(self._iter_candidates(value))
        candidates.sort(
            key=lambda item: (
                item.start_offset,
                -(item.end_offset - item.start_offset),
                item.nlp_type,
            )
        )
        selected: list[ExtractedEntity] = []
        occupied: list[tuple[int, int]] = []
        for candidate in candidates:
            if any(
                candidate.start_offset < end and candidate.end_offset > start
                for start, end in occupied
            ):
                continue
            selected.append(candidate)
            occupied.append((candidate.start_offset, candidate.end_offset))
        return sorted(selected, key=lambda item: (item.start_offset, item.end_offset, item.text))

    def _iter_candidates(self, value: ExtractionInput) -> Iterable[ExtractedEntity]:
        """Yield regex candidates with global position metadata."""

        for nlp_type, pattern in ENTITY_PATTERNS:
            for match in pattern.finditer(value.text):
                text = match.group(0).strip()
                leading_ws = len(match.group(0)) - len(match.group(0).lstrip())
                local_start = match.start() + leading_ws
                local_end = local_start + len(text)
                global_start = value.base_offset + local_start
                global_end = value.base_offset + local_end
                yield ExtractedEntity(
                    text=text,
                    nlp_type=nlp_type,
                    start_offset=global_start,
                    end_offset=global_end,
                    page_number=self._page_number(value.text, local_start, value.page_base),
                    paragraph_number=self._paragraph_number(value.text, local_start),
                    sentence_number=self._sentence_number(value.text, local_start),
                    context=self._context(value.text, local_start, local_end),
                )

    def _context(self, text: str, start: int, end: int) -> str:
        """Return a bounded context window around a detected entity."""

        left = max(0, start - self._context_chars)
        right = min(len(text), end + self._context_chars)
        return text[left:right].replace("\n", " ").strip()

    def _page_number(self, text: str, start: int, page_base: int) -> int:
        """Count form-feed page separators before the local entity start."""

        return page_base + text[:start].count("\f")

    def _paragraph_number(self, text: str, start: int) -> int:
        """Calculate one-based paragraph position inside the chunk."""

        return len(re.split(r"\n\s*\n", text[:start])) if text[:start] else 1

    def _sentence_number(self, text: str, start: int) -> int:
        """Calculate a simple one-based sentence position inside the chunk."""

        return max(1, len(re.findall(r"[.!?]\s+", text[:start])) + 1)
