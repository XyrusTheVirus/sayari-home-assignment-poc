"""Serializable Temporal workflow and activity contracts."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class DocumentProcessingWorkflowInput:
    """Workflow input containing only the durable run identifier."""

    run_id: UUID
