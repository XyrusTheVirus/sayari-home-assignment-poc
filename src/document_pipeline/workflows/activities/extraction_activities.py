"""Extraction task-queue activities."""

from uuid import UUID

from temporalio import activity

from document_pipeline.integrations.extractor import ExtractionInput
from document_pipeline.models.domain import TokenCreate
from document_pipeline.services.chunking_service import deterministic_uuid, normalized_hash
from document_pipeline.workflows.activities.run_activities import _deps


@activity.defn(name="extract_chunk_activity")
async def extract_chunk_activity(chunk_id: UUID) -> None:
    """Extract one bounded chunk and commit tokens with an idempotent checkpoint."""

    dependencies = _deps()
    async with dependencies.uow_factory.transaction() as uow:
        chunk = await uow.chunks.get(chunk_id)
        if chunk is None:
            raise ValueError(f"chunk {chunk_id} not found")
        should_run = await uow.chunks.mark_running(chunk_id)
        if not should_run:
            return
    text = await dependencies.store.get_text(chunk.object_uri)
    extracted = await dependencies.extractor.extract(
        ExtractionInput(text=text, base_offset=chunk.read_start, page_base=1)
    )
    owned = [item for item in extracted if chunk.core_start <= item.start_offset < chunk.core_end]
    tokens = [
        TokenCreate(
            id=deterministic_uuid(
                chunk.run_id,
                f"token:{item.start_offset}:{item.end_offset}:{normalized_hash(item.text)}",
            ),
            run_id=chunk.run_id,
            chunk_id=chunk.id,
            local_index=index,
            text=item.text,
            normalized_text_hash=normalized_hash(item.text),
            nlp_type=item.nlp_type,
            start_offset=item.start_offset,
            end_offset=item.end_offset,
            page_number=item.page_number,
            paragraph_number=item.paragraph_number,
            sentence_number=item.sentence_number,
            context=item.context,
        )
        for index, item in enumerate(owned)
    ]
    async with dependencies.uow_factory.transaction() as uow:
        await uow.tokens.bulk_upsert(tokens)
        await uow.chunks.mark_completed(chunk_id, len(tokens))
