"""Unit tests for deterministic mock extractor and classifier."""

from uuid import uuid4

import pytest

from document_pipeline.integrations.classifier import ClassificationInput
from document_pipeline.integrations.extractor import ExtractionInput
from document_pipeline.integrations.mock_classifier import MockClassifier
from document_pipeline.integrations.mock_extractor import MockExtractor
from document_pipeline.models.enums import Classification


@pytest.mark.asyncio
async def test_extractor_returns_offsets_and_metadata() -> None:
    """The mock extractor returns sorted entities with absolute offsets and metadata."""

    text = "John Smith works at Acme Corp.\fMaria Garcia visited 123 Main St on 2026-06-15."
    entities = await MockExtractor().extract(ExtractionInput(text=text, base_offset=10))
    values = {entity.text: entity for entity in entities}
    assert values["John Smith"].start_offset == 10
    assert values["Maria Garcia"].page_number == 2
    assert values["123 Main St"].nlp_type == "ADDRESS"


@pytest.mark.asyncio
async def test_classifier_maps_supported_labels() -> None:
    """The mock classifier maps common NLP labels to assignment classifications."""

    classifier = MockClassifier()
    result = await classifier.classify(
        ClassificationInput(uuid4(), "Acme Corp", "works at Acme Corp", "ORG")
    )
    assert result.classification == Classification.COMPANY
    assert 0 <= result.confidence <= 1
    assert result.reasoning
