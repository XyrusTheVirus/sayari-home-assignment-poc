"""Dependency construction for Temporal activities."""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncEngine

from document_pipeline.config import Settings, get_settings
from document_pipeline.infrastructure.database import create_engine, create_session_factory
from document_pipeline.infrastructure.storage import create_object_store
from document_pipeline.integrations.classifier import Classifier
from document_pipeline.integrations.extractor import Extractor
from document_pipeline.integrations.mock_classifier import MockClassifier
from document_pipeline.integrations.mock_extractor import MockExtractor
from document_pipeline.integrations.object_store import ObjectStore
from document_pipeline.repositories.unit_of_work import UnitOfWorkFactory
from document_pipeline.services.chunking_service import ChunkingService


@dataclass(slots=True)
class ActivityDependencies:
    """Activity dependency container shared by worker processes."""

    settings: Settings
    engine: AsyncEngine
    uow_factory: UnitOfWorkFactory
    store: ObjectStore
    extractor: Extractor
    classifier: Classifier
    chunking: ChunkingService

    async def close(self) -> None:
        """Release process resources."""

        await self.store.close()
        await self.engine.dispose()


def create_activity_dependencies() -> ActivityDependencies:
    """Create concrete dependencies from environment settings."""

    settings = get_settings()
    engine = create_engine(settings)
    return ActivityDependencies(
        settings=settings,
        engine=engine,
        uow_factory=UnitOfWorkFactory(create_session_factory(engine)),
        store=create_object_store(settings),
        extractor=MockExtractor(settings.mock_extractor_delay_ms),
        classifier=MockClassifier(settings.mock_classifier_delay_ms),
        chunking=ChunkingService(settings.chunk_target_chars, settings.chunk_overlap_chars),
    )
