"""Object-store dependency factories."""

from document_pipeline.config import Settings
from document_pipeline.integrations.minio_object_store import MinioObjectStore
from document_pipeline.integrations.object_store import ObjectStore


def create_object_store(settings: Settings) -> ObjectStore:
    """Create an S3-compatible object-store adapter for MinIO/local S3."""

    return MinioObjectStore(settings)
