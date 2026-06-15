"""Temporal client construction shared by API and worker entry points."""

from temporalio.client import Client

from document_pipeline.config import Settings


async def create_temporal_client(settings: Settings) -> Client:
    """Connect to Temporal using environment-derived namespace and address."""

    return await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
