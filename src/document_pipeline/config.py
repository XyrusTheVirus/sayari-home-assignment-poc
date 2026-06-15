"""Typed environment configuration for every service process."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and `.env` files."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8080
    database_url: str = "postgresql+asyncpg://pipeline:pipeline@localhost:5432/pipeline"
    temporal_address: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_workflow_task_queue: str = "document-workflows"
    temporal_extraction_task_queue: str = "extraction"
    temporal_classification_task_queue: str = "classification"
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "document-pipeline"
    s3_region: str = "us-east-1"
    max_source_bytes: int = Field(default=10_485_760, gt=0)
    chunk_target_chars: int = Field(default=4_000, gt=100)
    chunk_overlap_chars: int = Field(default=250, ge=0)
    extraction_insert_batch_size: int = Field(default=250, gt=0)
    classification_batch_size: int = Field(default=25, gt=0)
    classification_persist_batch_size: int = Field(default=5, gt=0)
    max_extraction_activities_per_document: int = Field(default=4, gt=0)
    max_classification_activities_per_document: int = Field(default=4, gt=0)
    extraction_worker_concurrency: int = Field(default=8, gt=0)
    classification_worker_concurrency: int = Field(default=8, gt=0)
    database_pool_size: int = Field(default=10, gt=0)
    mock_extractor_delay_ms: int = Field(default=20, ge=0)
    mock_classifier_delay_ms: int = Field(default=100, ge=0)

    @field_validator("chunk_overlap_chars")
    @classmethod
    def overlap_must_fit_chunk(cls, value: int, info: object) -> int:
        """Reject overlap sizes that would prevent forward chunk progress."""

        data = getattr(info, "data", {})
        target = int(data.get("chunk_target_chars", 4_000))
        if value >= target:
            raise ValueError("CHUNK_OVERLAP_CHARS must be smaller than CHUNK_TARGET_CHARS")
        return value


@lru_cache
def get_settings() -> Settings:
    """Return process-wide immutable settings with pydantic validation."""

    return Settings()
