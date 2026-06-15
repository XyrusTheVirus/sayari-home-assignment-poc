"""Deterministic mock classifier that mimics a provider adapter."""

import asyncio
import re

from document_pipeline.integrations.classifier import ClassificationInput, ClassificationResult
from document_pipeline.models.enums import Classification


class MockClassifier:
    """Rule-based classifier with realistic labels, confidence, and reasoning."""

    version = "mock-classifier-v1"
    model_version = "rules-2026-06"
    prompt_version = "prompt-v1"

    def __init__(self, delay_ms: int = 0) -> None:
        """Configure optional artificial latency for progress demonstrations."""

        self._delay_ms = delay_ms

    async def classify(self, value: ClassificationInput) -> ClassificationResult:
        """Classify a token using deterministic rules and bounded context."""

        if self._delay_ms:
            await asyncio.sleep(self._delay_ms / 1_000)
        text = value.text.strip()
        context = value.context or ""
        if value.nlp_type == "PERSON" or re.fullmatch(r"(?:Dr\.|Ms\.|Mr\.)?\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}", text):
            return self._result(Classification.PERSON, 0.94, "The token matches a full personal name.")
        if value.nlp_type == "ORG" or re.search(r"\b(Corp|Corporation|Inc|Ltd|LLC|Group|Technologies|Bank)\b", text):
            confidence = 0.96 if re.search(r"\b(works at|announced|acquired|subsidiary|headquartered)\b", context, re.I) else 0.9
            return self._result(Classification.COMPANY, confidence, "The token contains an organization suffix or company context.")
        if value.nlp_type == "ADDRESS" or re.search(r"\b\d{1,6}\s+.+\s+(St|Street|Ave|Road|Rd|Blvd|Lane|Drive|Dr)\b", text):
            return self._result(Classification.ADDRESS, 0.95, "The token follows a street-address pattern.")
        if value.nlp_type == "DATE" or re.search(r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}", text):
            return self._result(Classification.DATE, 0.93, "The token is formatted as a calendar date.")
        return self._result(Classification.UNKNOWN, 0.55, "The token is not specific enough for a supported category.")

    def _result(self, classification: Classification, confidence: float, reasoning: str) -> ClassificationResult:
        """Create a validated provider result."""

        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be in [0, 1]")
        return ClassificationResult(
            classification=classification,
            confidence=confidence,
            reasoning=reasoning,
            model_version=self.model_version,
            prompt_version=self.prompt_version,
        )
