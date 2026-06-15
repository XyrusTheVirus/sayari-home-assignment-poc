"""Progress and duration calculations for status responses."""

from datetime import datetime

from document_pipeline.models.domain import RunRecord, StageProgress


class ProgressService:
    """Calculates user-visible progress from persisted counters and timestamps."""

    def stage_duration_ms(
        self, started_at: datetime | None, completed_at: datetime | None
    ) -> int | None:
        """Return finalized wall-clock duration in milliseconds."""

        if started_at is None or completed_at is None:
            return None
        return int((completed_at - started_at).total_seconds() * 1_000)

    def extraction_progress(self, run: RunRecord) -> StageProgress:
        """Build extraction-stage progress from run counters."""

        return StageProgress(
            completed=run.completed_chunks,
            total=run.total_chunks,
            started_at=run.extraction_started_at,
            completed_at=run.extraction_completed_at,
            duration_ms=self.stage_duration_ms(
                run.extraction_started_at, run.extraction_completed_at
            ),
        )

    def classification_progress(self, run: RunRecord) -> StageProgress:
        """Build classification-stage progress from run counters."""

        return StageProgress(
            completed=run.classified_tokens,
            total=run.total_tokens,
            started_at=run.classification_started_at,
            completed_at=run.classification_completed_at,
            duration_ms=self.stage_duration_ms(
                run.classification_started_at, run.classification_completed_at
            ),
        )
