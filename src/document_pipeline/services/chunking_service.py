"""Deterministic bounded chunk creation and token normalization helpers."""

import hashlib
import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from uuid import UUID

from document_pipeline.integrations.object_store import ObjectStore
from document_pipeline.models.domain import ChunkManifest


@dataclass(frozen=True, slots=True)
class ChunkSlice:
    """In-memory chunk text and manifest metadata before object storage write."""

    chunk_index: int
    text: str
    read_start: int
    read_end: int
    core_start: int
    core_end: int


class ChunkingService:
    """Creates deterministic chunk manifests with overlap and canonical ownership."""

    def __init__(self, target_chars: int, overlap_chars: int) -> None:
        """Configure chunk size and overlap bounds."""

        self._target_chars = target_chars
        self._overlap_chars = overlap_chars

    def slice_text(self, text: str) -> list[ChunkSlice]:
        """Split text into deterministic chunks, preferring paragraph boundaries."""

        if not text:
            return []
        slices: list[ChunkSlice] = []
        core_start = 0
        index = 0
        while core_start < len(text):
            desired_end = min(len(text), core_start + self._target_chars)
            core_end = self._choose_boundary(text, core_start, desired_end)
            read_start = max(0, core_start - self._overlap_chars)
            read_end = min(len(text), core_end + self._overlap_chars)
            slices.append(
                ChunkSlice(
                    chunk_index=index,
                    text=text[read_start:read_end],
                    read_start=read_start,
                    read_end=read_end,
                    core_start=core_start,
                    core_end=core_end,
                )
            )
            core_start = core_end
            index += 1
        return slices

    async def create_chunk_objects(
        self,
        store: ObjectStore,
        run_id: UUID,
        text: str,
    ) -> list[ChunkManifest]:
        """Persist bounded chunk objects and return deterministic manifests."""

        manifests: list[ChunkManifest] = []
        for item in self.slice_text(text):
            chunk_id = deterministic_uuid(
                run_id, f"chunk:{item.chunk_index}:{item.core_start}:{item.core_end}"
            )
            key = f"runs/{run_id}/chunks/{item.chunk_index:06d}.txt"
            uri = await store.put_text(key, item.text)
            manifests.append(
                ChunkManifest(
                    id=chunk_id,
                    run_id=run_id,
                    chunk_index=item.chunk_index,
                    object_uri=uri,
                    read_start=item.read_start,
                    read_end=item.read_end,
                    core_start=item.core_start,
                    core_end=item.core_end,
                )
            )
        return manifests

    def _choose_boundary(self, text: str, start: int, desired_end: int) -> int:
        """Choose a stable boundary near the target end while ensuring progress."""

        if desired_end >= len(text):
            return len(text)
        search_start = max(start + 1, desired_end - max(200, self._target_chars // 4))
        paragraph = text.rfind("\n\n", search_start, desired_end)
        if paragraph > start:
            return paragraph + 2
        newline = text.rfind("\n", search_start, desired_end)
        if newline > start:
            return newline + 1
        space = text.rfind(" ", search_start, desired_end)
        if space > start:
            return space + 1
        return desired_end


def normalized_hash(text: str) -> str:
    """Return a SHA-256 hash of normalized token text for idempotency."""

    normalized = " ".join(text.casefold().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def deterministic_uuid(namespace: UUID, name: str) -> UUID:
    """Create a stable UUID5 for retry-safe chunks, tokens, and batches."""

    return uuid.uuid5(namespace, name)


def batched(values: list[object], size: int) -> Iterable[list[object]]:
    """Yield bounded list batches without relying on OFFSET/LIMIT semantics."""

    for index in range(0, len(values), size):
        yield values[index : index + size]
