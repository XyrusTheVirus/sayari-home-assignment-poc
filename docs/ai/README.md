# AI-Assisted Development Evidence

This repository was built with AI assistance from the implementation brief in
`docs/ai/prompts/001-poc-implementation.md`.

AI-assisted areas included the initial package layout, FastAPI schemas and controllers,
SQLAlchemy models, repository/service boundaries, Temporal workflow/activity wiring,
mock extractor/classifier logic, Docker Compose files, scripts, tests, and README text.

The engineer remains responsible for the code. The generated design was reviewed for the
assignment constraints: no Kafka, Temporal task queues for work distribution, PostgreSQL
as business state, MinIO as source-document storage, bounded chunks/batches, idempotent
classification progress, active-run publication after completion, and deterministic mock
providers.

Validation commands intended for review are:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
make demo
```

Do not treat a command as passed unless it is reported as executed in the final handoff.
