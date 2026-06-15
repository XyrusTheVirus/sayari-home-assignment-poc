"""Serializable Temporal workflow and activity contracts."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class DocumentProcessingWorkflowInput:
    """Workflow input containing only the durable run identifier."""

    run_id: UUID


@dataclass(frozen=True)
class ChunkIds:
    """Activity result containing extraction chunk IDs."""

    ids: list[UUID]


@dataclass(frozen=True)
class BatchIds:
    """Activity result containing classification batch IDs."""

    ids: list[UUID]
