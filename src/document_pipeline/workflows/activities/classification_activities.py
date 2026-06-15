"""Classification task-queue activities."""

from uuid import UUID

from temporalio import activity

from document_pipeline.integrations.classifier import ClassificationInput
from document_pipeline.workflows.activities.run_activities import _deps


@activity.defn(name="classify_batch_activity")
async def classify_batch_activity(batch_id: UUID) -> None:
    """Classify unfinished tokens in a stable batch and persist partial progress."""

    dependencies = _deps()
    async with dependencies.uow_factory.transaction() as uow:
        batch = await uow.batches.get(batch_id)
        if batch is None:
            raise ValueError(f"batch {batch_id} not found")
        should_run = await uow.batches.mark_running(batch_id)
        if not should_run:
            return
        tokens = await uow.tokens.get_unfinished_for_batch(batch)
    processed = 0
    for token in tokens:
        result = await dependencies.classifier.classify(
            ClassificationInput(
                token_id=token.id,
                text=token.text,
                context=token.context,
                nlp_type=token.nlp_type,
            )
        )
        async with dependencies.uow_factory.transaction() as uow:
            changed = await uow.tokens.complete_classification(
                run_id=batch.run_id,
                token_id=token.id,
                result=result,
                classifier_version=dependencies.classifier.version,
            )
            if changed:
                processed += 1
    async with dependencies.uow_factory.transaction() as uow:
        await uow.batches.mark_completed(batch_id, processed)
