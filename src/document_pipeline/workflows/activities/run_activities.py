"""Workflow-queue activities for run initialization/finalization."""

from uuid import UUID

from sqlalchemy import select
from temporalio import activity

from document_pipeline.errors import InvalidRunStateError
from document_pipeline.models.domain import BatchManifest
from document_pipeline.models.enums import WorkStatus
from document_pipeline.models.orm.token import TokenORM
from document_pipeline.services.chunking_service import deterministic_uuid
from document_pipeline.workflows.activities.dependencies import ActivityDependencies

deps: ActivityDependencies | None = None


def configure(dependencies: ActivityDependencies) -> None:
    """Set process-local dependencies for activity functions."""

    global deps
    deps = dependencies


def _deps() -> ActivityDependencies:
    """Return configured dependencies or fail fast during worker startup issues."""

    if deps is None:
        raise RuntimeError("activities are not configured")
    return deps


@activity.defn(name="initialize_run_activity")
async def initialize_run_activity(run_id: UUID) -> list[UUID]:
    """Chunk the immutable source, persist manifests, and mark extraction started."""

    dependencies = _deps()
    async with dependencies.uow_factory.transaction() as uow:
        run = await uow.runs.get(run_id)
        if run is None:
            raise InvalidRunStateError(f"run {run_id} not found")
        source_uri = run.source_uri
    text = await dependencies.store.get_text(source_uri)
    chunks = await dependencies.chunking.create_chunk_objects(dependencies.store, run_id, text)
    async with dependencies.uow_factory.transaction() as uow:
        await uow.chunks.bulk_create(chunks)
        await uow.runs.mark_extraction_started(run_id, len(chunks))
    return [chunk.id for chunk in chunks]


@activity.defn(name="finalize_extraction_activity")
async def finalize_extraction_activity(run_id: UUID) -> list[UUID]:
    """Verify extraction barrier, finalize token count, and materialize batches."""

    dependencies = _deps()
    async with dependencies.uow_factory.transaction() as uow:
        if await uow.chunks.incomplete_count(run_id) != 0:
            raise InvalidRunStateError("cannot finalize extraction before every chunk completes")
        total_tokens = await uow.tokens.count_by_run(run_id)
        await uow.runs.finalize_extraction(run_id, total_tokens)
        batches = await _build_batches(dependencies, run_id)
        await uow.batches.bulk_create(batches)
    return [batch.id for batch in batches]


@activity.defn(name="start_classification_activity")
async def start_classification_activity(run_id: UUID) -> None:
    """Transition the run into CLASSIFYING after the extraction barrier."""

    async with _deps().uow_factory.transaction() as uow:
        await uow.runs.mark_classification_started(run_id)


@activity.defn(name="finalize_run_activity")
async def finalize_run_activity(run_id: UUID) -> None:
    """Verify all batches completed, complete run, and publish active result."""

    async with _deps().uow_factory.transaction() as uow:
        run = await uow.runs.get(run_id)
        if run is None:
            raise InvalidRunStateError(f"run {run_id} not found")
        if await uow.batches.incomplete_count(run_id) != 0:
            raise InvalidRunStateError("cannot complete run before every batch completes")
        await uow.runs.finalize_completed(run_id)
        await uow.documents.publish_active_run(run.document_id, run_id)


@activity.defn(name="record_run_failure_activity")
async def record_run_failure_activity(args: tuple[UUID, str, str]) -> None:
    """Best-effort failure recording activity used by workflow exception handling."""

    run_id, code, detail = args
    async with _deps().uow_factory.transaction() as uow:
        await uow.runs.mark_failed(run_id, code, detail)


async def _build_batches(dependencies: ActivityDependencies, run_id: UUID) -> list[BatchManifest]:
    """Create stable classification batches by chunk-local token ranges."""

    batches: list[BatchManifest] = []
    async with dependencies.engine.connect() as connection:
        rows = (
            await connection.execute(
                select(TokenORM.chunk_id, TokenORM.local_index)
                .where(TokenORM.run_id == run_id)
                .order_by(TokenORM.chunk_id, TokenORM.local_index)
            )
        ).all()
    grouped: dict[UUID, list[int]] = {}
    for chunk_id, local_index in rows:
        grouped.setdefault(chunk_id, []).append(local_index)
    size = dependencies.settings.classification_batch_size
    for chunk_id, indices in grouped.items():
        for start in range(0, len(indices), size):
            window = indices[start : start + size]
            batch_id = deterministic_uuid(run_id, f"batch:{chunk_id}:{window[0]}:{window[-1]}")
            batches.append(
                BatchManifest(batch_id, run_id, chunk_id, window[0], window[-1], WorkStatus.PENDING)
            )
    return batches
