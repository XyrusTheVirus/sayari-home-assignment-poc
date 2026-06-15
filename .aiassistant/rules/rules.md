---
apply: always
---

# IDE Code Agent Implementation Specification
## Document Processing Pipeline — Working POC

> **Purpose:** This file is the authoritative implementation brief for an IDE coding agent. Build the complete working POC described here. Do not only scaffold files. The repository must run locally, demonstrate the required scenarios end to end, and be ready for review as a senior software engineer home assignment.

---

## 1. Mission

Implement a clean, resilient, well-tested Python monorepo for a two-stage document-processing pipeline:

1. **Extraction** scans a document and stores entity candidates as individual tokens.
2. **Classification** classifies every extracted token as `COMPANY`, `PERSON`, `ADDRESS`, `DATE`, or `UNKNOWN`.

The system must:

- scale the API, extraction workers, and classification workers independently;
- process large inputs in bounded chunks and token batches;
- resume after partial failure without redoing completed work;
- support a full rerun that cleanly replaces the active result;
- expose progress and stage durations;
- run locally with one command;
- use clean interfaces for NLP and LLM integrations, with deterministic mock implementations;
- include realistic small, medium, and large sample documents;
- include integration tests and an executable demo script;
- include a complete `README.md`;
- preserve the prompts used with the coding agent in the repository.

Do not add Kafka to this POC. Temporal task queues are the work-distribution mechanism. PostgreSQL is the business-state source of truth, Temporal is the workflow-execution source of truth, and MinIO is the source of truth for source-document content.

---

## 2. Non-negotiable architecture

Use this stack:

| Concern | Required choice |
|---|---|
| Language | Python 3.12 or newer |
| HTTP API | FastAPI + Pydantic v2 |
| Orchestration | Temporal Python SDK |
| Database | PostgreSQL + SQLAlchemy 2.x async ORM |
| Migrations | Alembic |
| Object storage | S3-compatible client, MinIO locally |
| Local environment | Docker Compose |
| Tests | Pytest, pytest-asyncio, HTTPX |
| Configuration | `pydantic-settings` and environment variables |
| Logging | Structured JSON logging with correlation fields |
| Dependency management | `uv` with a committed lock file |

The API and all worker processes may share one application image but must run as separate services with separate commands and Temporal task queues.

### Required runtime services

- `api`
- `workflow-worker`
- `extraction-worker`
- `classification-worker`
- `postgres`
- `temporal`
- `temporal-ui`
- `minio`
- `minio-init` or equivalent bucket-initialization job
- `migration` one-shot service or equivalent startup migration command

### Required Temporal task queues

- `document-workflows`
- `extraction`
- `classification`

### Required processing model

```text
API request
  -> create immutable source object and versioned run
  -> start DocumentProcessingWorkflow(run_id)
  -> create deterministic extraction chunks
  -> run bounded extraction activities
  -> extraction barrier: all chunks complete
  -> finalize exact total_tokens
  -> materialize stable classification batches
  -> run bounded classification activities
  -> finalize run
  -> atomically publish documents.active_run_id
```

Classification must not begin before extraction finalization. This is intentional so `total_tokens` is exact before classification starts.

---

## 3. Repository structure

Use one Python repository with one installable application package and separate service entry points. Keep domain, API, service, repository, integration, workflow, and infrastructure concerns distinct.

Create at least the following structure:

```text
.
├── README.md
├── pyproject.toml
├── uv.lock
├── compose.yaml
├── Dockerfile
├── .dockerignore
├── .gitignore
├── .env.example
├── Makefile
├── start.sh
├── alembic.ini
├── migrations/
│   ├── env.py
│   └── versions/
├── src/
│   └── document_pipeline/
│       ├── __init__.py
│       ├── config.py
│       ├── logging.py
│       ├── errors.py
│       ├── api/
│       │   ├── main.py
│       │   ├── dependencies.py
│       │   ├── exception_handlers.py
│       │   ├── controllers/
│       │   │   ├── health_controller.py
│       │   │   ├── process_controller.py
│       │   │   └── documents_controller.py
│       │   └── validations/
│       │       ├── common.py
│       │       ├── process_requests.py
│       │       ├── process_responses.py
│       │       ├── document_requests.py
│       │       └── document_responses.py
│       ├── models/
│       │   ├── enums.py
│       │   ├── domain.py
│       │   └── orm/
│       │       ├── base.py
│       │       ├── document.py
│       │       ├── document_run.py
│       │       ├── document_chunk.py
│       │       ├── token.py
│       │       └── classification_batch.py
│       ├── repositories/
│       │   ├── interfaces.py
│       │   ├── unit_of_work.py
│       │   └── postgres/
│       │       ├── document_repository.py
│       │       ├── run_repository.py
│       │       ├── chunk_repository.py
│       │       ├── token_repository.py
│       │       └── batch_repository.py
│       ├── services/
│       │   ├── processing_service.py
│       │   ├── document_query_service.py
│       │   ├── rerun_service.py
│       │   ├── progress_service.py
│       │   └── chunking_service.py
│       ├── integrations/
│       │   ├── extractor.py
│       │   ├── classifier.py
│       │   ├── object_store.py
│       │   ├── mock_extractor.py
│       │   ├── mock_classifier.py
│       │   └── minio_object_store.py
│       ├── workflows/
│       │   ├── contracts.py
│       │   ├── document_processing_workflow.py
│       │   └── activities/
│       │       ├── run_activities.py
│       │       ├── extraction_activities.py
│       │       └── classification_activities.py
│       ├── workers/
│       │   ├── workflow_worker.py
│       │   ├── extraction_worker.py
│       │   └── classification_worker.py
│       └── infrastructure/
│           ├── database.py
│           ├── temporal.py
│           └── storage.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── conftest.py
│   └── fixtures/
├── test_documents/
│   ├── small.txt
│   ├── medium.txt
│   └── large.txt
├── scripts/
│   ├── demo.sh
│   ├── wait-for-services.sh
│   └── generate_large_document.py
└── docs/
    └── ai/
        ├── README.md
        └── prompts/
            └── 001-poc-implementation.md
```

Small deviations are acceptable only when they improve clarity. The following layers are mandatory and must be visible in the codebase:

- controllers;
- models;
- validations;
- repositories;
- services.

Do not put business logic in FastAPI controllers or Temporal worker entry points.

---

## 4. Coding and design rules

### 4.1 General

- Use full type annotations.
- Prefer small cohesive modules and dependency injection.
- Use async I/O for HTTP, PostgreSQL, and Temporal integration.
- Use timezone-aware UTC timestamps.
- Use UUIDs internally.
- Do not use global mutable state for business progress.
- Do not use in-memory queues as durable workflow state.
- Do not use `OFFSET/LIMIT` for worker assignment.
- Do not pass whole documents or unbounded token arrays through Temporal payloads.
- Do not expose raw database exceptions to clients.
- Avoid circular imports and service-locator patterns.
- Avoid repository methods that return ORM objects outside the persistence layer when a domain object or DTO is more appropriate.
- Keep transactions short and explicit.
- Keep external calls outside long-running database transactions.

### 4.2 Quality tools

Configure and make these commands pass:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest
```

Use a strict but practical MyPy configuration. Add coverage reporting. Target meaningful coverage of services, repositories, workflow logic, and API validation rather than chasing a superficial percentage.

### 4.3 Error taxonomy

Define explicit exceptions, for example:

- `DocumentNotFoundError`
- `RunNotFoundError`
- `RunConflictError`
- `InvalidRunStateError`
- `ObjectStoreUnavailableError`
- `RetryableInfrastructureError`
- `PermanentExtractionError`
- `PermanentClassificationError`

Map domain errors to stable HTTP responses in one FastAPI exception-handler module. Temporal activities must distinguish retryable infrastructure/provider errors from permanent validation/data errors.

---

## 5. Domain and persistence model

Implement SQLAlchemy models, domain types, Alembic migrations, constraints, and indexes for all tables below.

### 5.1 Enums

```python
class RunStatus(StrEnum):
    PENDING = "PENDING"
    EXTRACTING = "EXTRACTING"
    CLASSIFICATION_PENDING = "CLASSIFICATION_PENDING"
    CLASSIFYING = "CLASSIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TokenStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Classification(StrEnum):
    COMPANY = "COMPANY"
    PERSON = "PERSON"
    ADDRESS = "ADDRESS"
    DATE = "DATE"
    UNKNOWN = "UNKNOWN"
```

### 5.2 `documents`

| Column | Type | Requirement |
|---|---|---|
| `id` | UUID PK | Internal stable identifier. |
| `external_id` | VARCHAR unique | API-facing value such as `doc-123`. |
| `active_run_id` | UUID nullable FK | Latest successfully completed run. |
| `created_at` | TIMESTAMPTZ | Creation timestamp. |
| `updated_at` | TIMESTAMPTZ | Last metadata/publication change. |

### 5.3 `document_runs`

| Column | Type | Requirement |
|---|---|---|
| `id` | UUID PK | Unique processing attempt. |
| `document_id` | UUID FK | Parent document. |
| `version` | INTEGER | Monotonic per-document version. |
| `source_uri` | TEXT | Immutable MinIO/S3 object URI. |
| `source_checksum` | VARCHAR(64) | SHA-256 of source text. |
| `status` | enum | Current run state. |
| `total_chunks` | INTEGER | Deterministic extraction chunk count. |
| `completed_chunks` | INTEGER | Successfully committed chunks. |
| `total_tokens` | INTEGER nullable until finalization | Exact count after extraction barrier. |
| `classified_tokens` | INTEGER | Durably completed tokens. |
| `extraction_started_at` | TIMESTAMPTZ nullable | Set once. |
| `extraction_completed_at` | TIMESTAMPTZ nullable | Set after final extraction commit. |
| `classification_started_at` | TIMESTAMPTZ nullable | Set once after barrier. |
| `classification_completed_at` | TIMESTAMPTZ nullable | Set after all batches complete. |
| `extractor_version` | TEXT | Reproducibility metadata. |
| `classifier_version` | TEXT | Reproducibility metadata. |
| `model_version` | TEXT nullable | Mock/real model identifier. |
| `prompt_version` | TEXT nullable | Prompt revision. |
| `error_code` | TEXT nullable | Stable machine-readable failure. |
| `error_detail` | TEXT nullable | Sanitized diagnostic. |
| `created_at` | TIMESTAMPTZ | Created time. |
| `updated_at` | TIMESTAMPTZ | Last state/progress change. |

Constraints:

- `UNIQUE(document_id, version)`;
- all counters non-negative;
- `completed_chunks <= total_chunks`;
- after extraction finalization, `classified_tokens <= total_tokens`.

### 5.4 `document_chunks`

| Column | Type | Requirement |
|---|---|---|
| `id` | UUID PK | Stable extraction work ID. |
| `run_id` | UUID FK | Owning run. |
| `chunk_index` | INTEGER | Deterministic order. |
| `object_uri` | TEXT | Derived chunk object stored in MinIO. |
| `read_start` / `read_end` | BIGINT | Global character range including overlap. |
| `core_start` / `core_end` | BIGINT | Canonical ownership range. |
| `status` | enum | Work state. |
| `attempts` | INTEGER | Execution count. |
| `extracted_token_count` | INTEGER | Tokens committed by this chunk. |
| `started_at` / `completed_at` | TIMESTAMPTZ nullable | Work timing. |
| `error_code` / `error_detail` | TEXT nullable | Failure information. |

Constraint: `UNIQUE(run_id, chunk_index)`.

### 5.5 `tokens`

| Column | Type | Requirement |
|---|---|---|
| `id` | UUID PK | Prefer deterministic UUID5 from run and canonical span. |
| `run_id` | UUID FK | Processing-version isolation. |
| `chunk_id` | UUID FK | Producing extraction checkpoint. |
| `local_index` | INTEGER | Stable order within chunk. |
| `text` | TEXT | Extracted text. |
| `normalized_text_hash` | VARCHAR(64) | Retry idempotency. |
| `nlp_type` | TEXT | Extractor label such as PERSON, ORG, GPE, DATE. |
| `start_offset` | BIGINT | Absolute inclusive character offset. |
| `end_offset` | BIGINT | Absolute exclusive character offset. |
| `page_number` | INTEGER nullable | Page filter support. |
| `paragraph_number` | INTEGER nullable | Position metadata. |
| `sentence_number` | INTEGER nullable | Position metadata. |
| `context` | TEXT nullable | Bounded surrounding text for classification. |
| `classification_status` | enum | Pending/completed/failed. |
| `classification` | enum nullable | COMPANY/PERSON/ADDRESS/DATE/UNKNOWN. |
| `confidence` | DOUBLE PRECISION nullable | Validate `0 <= value <= 1`. |
| `reasoning` | TEXT nullable | Short classifier explanation. |
| `classifier_version` | TEXT nullable | Result reproducibility. |
| `model_version` | TEXT nullable | Result reproducibility. |
| `prompt_version` | TEXT nullable | Result reproducibility. |
| `classified_at` | TIMESTAMPTZ nullable | Durable completion time. |
| `created_at` / `updated_at` | TIMESTAMPTZ | Audit times. |

Idempotency constraint:

```sql
UNIQUE (run_id, start_offset, end_offset, normalized_text_hash)
```

Required indexes:

```sql
CREATE INDEX ix_tokens_run_page
    ON tokens (run_id, page_number, start_offset, id);

CREATE INDEX ix_tokens_run_classification
    ON tokens (run_id, classification, id);

CREATE INDEX ix_tokens_pending
    ON tokens (run_id, chunk_id, local_index)
    WHERE classification_status = 'PENDING';
```

### 5.6 `classification_batches`

| Column | Type | Requirement |
|---|---|---|
| `id` | UUID PK | Stable activity ID. |
| `run_id` | UUID FK | Owning run. |
| `chunk_id` | UUID FK | Token-producing chunk. |
| `start_local_index` | INTEGER | Inclusive range start. |
| `end_local_index` | INTEGER | Inclusive range end. |
| `status` | enum | Work state. |
| `processed_count` | INTEGER | Durable completions attributed to the batch. |
| `attempts` | INTEGER | Activity executions. |
| `started_at` / `completed_at` | TIMESTAMPTZ nullable | Work timing. |
| `error_code` / `error_detail` | TEXT nullable | Failure information. |

Constraint:

```sql
UNIQUE (run_id, chunk_id, start_local_index, end_local_index)
```

### 5.7 Atomic progress updates

A duplicate retry must not increment progress twice. Use conditional updates and count actual transitions. Implement this logic in the repository/service layer, not in controllers.

Equivalent SQL behavior:

```sql
WITH completed AS (
  UPDATE tokens
     SET classification_status = 'COMPLETED',
         classification = :classification,
         confidence = :confidence,
         reasoning = :reasoning,
         classified_at = NOW(),
         updated_at = NOW()
   WHERE id = :token_id
     AND classification_status <> 'COMPLETED'
  RETURNING run_id
)
UPDATE document_runs
   SET classified_tokens = classified_tokens + 1,
       updated_at = NOW()
 WHERE id IN (SELECT run_id FROM completed);
```

The implementation may persist a small result sub-batch in one transaction, but it must increment `classified_tokens` only by the number of rows that actually transitioned.

---

## 6. API layer requirements

Controllers must only validate/translate HTTP concerns and call services. Repositories must never be called directly by controllers.

Use `/api/v1` as the main prefix, while also adding compatibility aliases for the exact assignment paths where useful.

### 6.1 Health

```http
GET /health/live
GET /health/ready
```

- Liveness returns success when the process is alive.
- Readiness checks PostgreSQL, Temporal connectivity, and MinIO bucket access with short timeouts.

### 6.2 Start processing

Required compatibility endpoint:

```http
POST /process
Content-Type: application/json
```

Preferred versioned endpoint:

```http
POST /api/v1/process
Content-Type: application/json
```

Request:

```json
{
  "document_id": "doc-123",
  "text": "John Smith works at Acme Corp, located at 123 Main St."
}
```

Validation:

- `document_id`: trimmed, 1–128 characters, safe slug characters only;
- `text`: non-empty after trimming;
- enforce configurable `MAX_SOURCE_BYTES` and return HTTP 413 when exceeded;
- reject control-only input;
- do not log the complete document body.

Behavior:

1. Resolve or create the logical `documents` row by `external_id`.
2. Create a new versioned run under a row lock or equivalent concurrency-safe mechanism.
3. Store the immutable source in MinIO.
4. Persist checksum and source URI.
5. Start the Temporal workflow using a stable workflow ID such as `document-run/{run_id}`.
6. Return HTTP 202.

Response:

```json
{
  "document_id": "doc-123",
  "run_id": "8ef32aac-4de8-4b89-a3df-6edb5d579fe7",
  "version": 1,
  "status": "PENDING",
  "status_url": "/documents/doc-123/status"
}
```

### 6.3 Full rerun

```http
POST /api/v1/documents/{document_id}/rerun
```

Also allow:

```http
POST /api/v1/documents/{document_id}/runs
```

Request accepts either new text or an explicit instruction to reuse the previous source:

```json
{
  "text": "Updated document contents...",
  "reuse_source": false
}
```

Rules:

- exactly one of new `text` or `reuse_source=true` must be valid;
- create a new isolated run;
- do not delete or modify active-run tokens during processing;
- switch `active_run_id` only after the new run completes;
- return HTTP 202 with the new `run_id` and version.

### 6.4 Status

Required compatibility endpoint:

```http
GET /documents/{document_id}/status
```

Preferred endpoint:

```http
GET /api/v1/documents/{document_id}/status
```

Optional query parameter:

- `run_id` to inspect a specific historical or in-progress run;
- without `run_id`, return the latest run, while clearly including `active_run_id`.

Response must include:

```json
{
  "document_id": "doc-123",
  "run_id": "...",
  "active_run_id": "...",
  "version": 2,
  "status": "CLASSIFYING",
  "extraction": {
    "completed_chunks": 12,
    "total_chunks": 12,
    "started_at": "2026-06-15T10:00:00Z",
    "completed_at": "2026-06-15T10:00:05Z",
    "duration_ms": 5000
  },
  "classification": {
    "processed_count": 150,
    "total_tokens": 500,
    "started_at": "2026-06-15T10:00:05Z",
    "completed_at": null,
    "duration_ms": null
  },
  "error": null
}
```

During extraction, `total_tokens` may be `null`. After the extraction barrier it must be exact.

### 6.5 Query tokens

Required compatibility endpoint:

```http
GET /documents/{document_id}/tokens?classification=PERSON
```

Preferred endpoint:

```http
GET /api/v1/documents/{document_id}/tokens
```

Support filters:

- `classification`;
- `page_number`;
- `nlp_type`;
- `classification_status`;
- optional `run_id` for historical/debug reads;
- `limit`, constrained to 1–200;
- opaque cursor for keyset pagination.

Default reads must use `documents.active_run_id`. Do not show a partially completed full rerun as the active result.

Return:

```json
{
  "items": [
    {
      "id": "...",
      "text": "John Smith",
      "nlp_type": "PERSON",
      "classification": "PERSON",
      "confidence": 0.98,
      "reasoning": "The extractor identified a full personal name.",
      "page_number": 1,
      "paragraph_number": 1,
      "sentence_number": 1,
      "start_offset": 0,
      "end_offset": 10
    }
  ],
  "next_cursor": null
}
```

Use keyset pagination ordered by `(page_number NULLS LAST, start_offset, id)` or another deterministic indexed order. Do not use high-offset pagination.

### 6.6 API behavior

- Return JSON problem details or another consistent error schema.
- Use HTTP 404 for missing documents/runs.
- Use HTTP 409 for invalid state conflicts.
- Use HTTP 422 for validation errors.
- Use HTTP 503 for dependency readiness failures.
- Add request IDs and include them in structured logs and responses.
- Generate OpenAPI automatically and keep request/response schemas explicit.

---

## 7. Application services

Implement at least these services:

### `ProcessingService`

Responsibilities:

- validate application-level invariants;
- create/resolve a logical document;
- create the versioned run safely;
- persist the source object and checksum;
- start the Temporal workflow;
- compensate cleanly if workflow start fails after run creation, by leaving an explicit retryable/failed state rather than silently losing the run.

### `RerunService`

Responsibilities:

- create a new run version;
- reuse or replace the source;
- never mutate the active run in place;
- start a new workflow;
- preserve the old active result until successful publication.

### `DocumentQueryService`

Responsibilities:

- resolve external document IDs;
- resolve active/latest/specific run semantics;
- return status DTOs;
- query tokens through repository filters and keyset cursors.

### `ProgressService`

Responsibilities:

- calculate user-visible progress;
- calculate finalized wall-clock stage durations;
- optionally calculate elapsed duration for an in-progress stage in a separate field;
- keep persisted counters consistent with actual state transitions.

### `ChunkingService`

Responsibilities:

- produce deterministic bounded chunks;
- use paragraph/newline boundaries where possible;
- add configurable overlap for cross-boundary entities;
- track global character offsets;
- create derived chunk objects in MinIO so extraction workers read one bounded object rather than the whole source;
- assign each chunk a read range and a non-overlapping core range.

The chunker should stream or incrementally process the source and must not require all source bytes plus all chunks to remain in memory simultaneously. Since the required API accepts JSON text, the inbound request itself is materialized by FastAPI, but downstream chunking and workers must remain bounded.

---

## 8. Repository contracts

Define repository protocols/interfaces and PostgreSQL implementations. Use a unit-of-work abstraction or an explicit transaction manager.

Required capabilities include:

### Document repository

- get by external ID;
- create if absent without duplicate races;
- lock document for creating the next run version;
- update `active_run_id` atomically;
- get active run.

### Run repository

- create run;
- get run;
- transition status with expected-current-state guard;
- set stage timestamps only once;
- update chunk counters idempotently;
- finalize exact `total_tokens`;
- update classified count by actual token transitions;
- mark failed with sanitized error information.

### Chunk repository

- bulk create deterministic manifests;
- get chunk;
- mark running;
- atomically persist chunk completion metadata;
- list incomplete chunks;
- count completed chunks.

### Token repository

- bulk upsert extracted tokens;
- count tokens by run;
- query unfinished tokens for a stable classification batch;
- conditionally persist classification results;
- query active/historical tokens with filters and keyset pagination.

### Batch repository

- bulk create stable batches;
- get batch;
- mark running/completed/failed;
- list incomplete batches;
- count completed batches.

Use `SELECT ... FOR UPDATE` only where needed. Do not hold database locks while calling MinIO or the classifier.

---

## 9. NLP extraction interface and mock

Define a provider-neutral interface:

```python
@dataclass(frozen=True, slots=True)
class ExtractionInput:
    text: str
    base_offset: int
    page_base: int = 1


@dataclass(frozen=True, slots=True)
class ExtractedEntity:
    text: str
    nlp_type: str
    start_offset: int
    end_offset: int
    page_number: int | None
    paragraph_number: int | None
    sentence_number: int | None
    context: str


class Extractor(Protocol):
    version: str

    async def extract(self, value: ExtractionInput) -> Sequence[ExtractedEntity]:
        ...
```

Implement `MockExtractor` as a deterministic, realistic rule-based adapter. It must detect at least:

- people with common full-name patterns;
- organizations with suffixes such as `Corp`, `Corporation`, `Inc`, `Ltd`, `LLC`, `Group`, `Technologies`, `Bank`;
- addresses with street numbers and common street suffixes;
- dates in several common textual/numeric formats;
- a small configured list of locations as `GPE` where useful.

Requirements:

- return `text`, `nlp_type`, sentence/paragraph/page numbers, and absolute character offsets;
- return a bounded context window around each entity;
- sort results by source offset;
- resolve duplicate/overlapping matches deterministically;
- inspect chunk overlap but persist only entities whose start offset is inside the chunk's core range;
- support form-feed (`\f`) as a page separator for page-number tests;
- expose a configurable artificial delay for progress/recovery demonstrations;
- never make network calls.

The extractor must be injected through the interface so a real NLP implementation can replace it later without changing services, activities, or repositories.

---

## 10. Classification interface and mock

Define a provider-neutral interface:

```python
@dataclass(frozen=True, slots=True)
class ClassificationInput:
    token_id: UUID
    text: str
    context: str | None
    nlp_type: str


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    classification: Classification
    confidence: float
    reasoning: str
    model_version: str
    prompt_version: str | None


class Classifier(Protocol):
    version: str

    async def classify(self, value: ClassificationInput) -> ClassificationResult:
        ...
```

Implement `MockClassifier` with realistic deterministic rules:

- `PERSON` NLP type or full-name pattern -> `PERSON`;
- `ORG` plus organization suffix/context -> `COMPANY`;
- address pattern -> `ADDRESS`;
- date pattern or `DATE` NLP type -> `DATE`;
- otherwise -> `UNKNOWN`.

Return meaningful confidence values and concise reasoning. Validate confidence within `0..1`.

Add environment-configurable latency, for example `MOCK_CLASSIFIER_DELAY_MS`, so progress can be observed and a worker can be stopped during the demo. Do not intentionally fail in normal operation. Any test-only fault injection must be disabled by default and clearly named.

The classifier activity must:

- load only unfinished tokens assigned to its batch;
- classify a bounded number at a time;
- persist results per token or in small sub-batches so partial progress survives a crash;
- avoid holding a database transaction during classifier execution;
- conditionally update token state and increment progress only for actual transitions;
- skip already completed tokens on retry.

---

## 11. Temporal workflow and activities

### 11.1 Workflow contract

```python
@dataclass(frozen=True)
class DocumentProcessingWorkflowInput:
    run_id: UUID
```

Use the `run_id` as the only required workflow input. Load mutable business state through activities, not directly from workflow code.

### 11.2 Workflow sequence

Implement `DocumentProcessingWorkflow` with these steps:

1. `initialize_run_activity(run_id)`
   - guarded transition `PENDING -> EXTRACTING`;
   - set `extraction_started_at` once;
   - stream/chunk the source, store derived chunk objects, and persist deterministic chunk manifests;
   - return chunk IDs.
2. Schedule extraction activities on the `extraction` queue.
   - enforce configurable `MAX_EXTRACTION_ACTIVITIES_PER_DOCUMENT`;
   - do not create unbounded in-memory activity lists;
   - process IDs in bounded windows if necessary.
3. `finalize_extraction_activity(run_id)`
   - verify every chunk is complete;
   - count tokens from durable rows;
   - set exact `total_tokens`;
   - set `extraction_completed_at` once;
   - transition to `CLASSIFICATION_PENDING`;
   - create stable classification batches;
   - return batch IDs.
4. `start_classification_activity(run_id)`
   - guarded transition to `CLASSIFYING`;
   - set `classification_started_at` once.
5. Schedule classification activities on the `classification` queue.
   - enforce configurable per-document concurrency;
   - use batch IDs, never token arrays.
6. `finalize_run_activity(run_id)`
   - verify all batches are complete and `classified_tokens == total_tokens`;
   - set `classification_completed_at`;
   - mark run `COMPLETED`;
   - atomically update `documents.active_run_id` to this run.
7. On terminal workflow failure, call a best-effort failure-recording activity that marks the run failed without overwriting an already completed run.

Temporal workflow code must remain deterministic. Do not perform database access, filesystem access, random UUID generation, current-time calls, or network I/O directly inside workflow code.

### 11.3 Activity retry behavior

Configure explicit start-to-close timeouts and retry policies.

Recommended behavior:

- database/object-store temporary failures: retry with exponential backoff;
- classifier timeout/rate limit: retry with backoff and jitter where supported;
- invalid source or deterministic malformed data: non-retryable;
- bounded maximum attempts for permanent-looking failures;
- activity heartbeat for longer extraction/classification activities;
- heartbeat details may include chunk/batch ID and last local index.

Do not claim exactly-once external classifier execution. Guarantee at-least-once activity execution with idempotent persistence.

### 11.4 Worker configuration

Each worker entry point must:

- initialize structured logging;
- initialize required dependencies;
- register only its workflows/activities;
- use the correct task queue;
- expose configurable worker concurrency;
- shut down gracefully on SIGTERM/SIGINT;
- close database/storage clients.

---

## 12. Recovery and rerun behavior

### 12.1 Partial extraction recovery

Each extraction chunk is a checkpoint.

- Persist all tokens for one bounded chunk and mark the chunk complete transactionally when practical.
- If a chunk retries after commit but before Temporal acknowledgement, token upserts and the guarded chunk transition must be harmless.
- Completed chunks must not be extracted again during workflow recovery.
- Classification must not start until all chunks are complete.

### 12.2 Partial classification recovery

Required scenario:

- extraction produced 100 tokens;
- 30 tokens were classified;
- classification worker stops;
- after restart, the same run resumes from 30/100;
- the 30 completed tokens are not reclassified or recounted;
- only the remaining 70 are processed.

Persist token results frequently enough for this scenario to be observable.

### 12.3 Full rerun

- Create a new run version and new source object when text changes.
- Scope chunks, tokens, and batches to the new run.
- Keep the old active run readable while the new run is processing.
- Atomically switch the active run only after successful completion.
- Default token queries must then return only the new run's data.
- Retain historical runs for inspection; deletion can be an explicit future concern.

### 12.4 Reconciliation

Add a small reconciliation service or command that can recompute derived counters for a run:

- `completed_chunks` from completed chunk rows;
- `total_tokens` after extraction from token count;
- `classified_tokens` from completed token rows;
- completed-batch count.

It should report or repair safe derived-counter drift without redoing successful extraction/classification.

---

## 13. Progress and duration tracking

Persist these timestamps:

- `extraction_started_at`;
- `extraction_completed_at`;
- `classification_started_at`;
- `classification_completed_at`.

Set each timestamp once through guarded state transitions.

Final duration formulas:

```text
extraction_duration = extraction_completed_at - extraction_started_at
classification_duration = classification_completed_at - classification_started_at
```

The status endpoint must show:

- extraction chunks completed / total chunks;
- classification `processed_count / total_tokens`;
- final stage durations;
- stage status;
- error information when failed.

Do not double-count parallel worker time. User-visible duration is wall-clock stage duration.

---

## 14. Large-document and resource-safety behavior

Even though the assignment sample documents are modest, implement bounded work units:

- configurable target chunk size;
- configurable overlap size;
- bounded extraction concurrency globally and per document;
- configurable classification batch size;
- configurable classifier sub-batch size;
- bounded database pool;
- bounded worker concurrency;
- bounded MinIO read buffers;
- no whole-document payloads in Temporal;
- no one-activity-per-token fan-out;
- no unbounded `asyncio.gather`.

A single large document must not monopolize all workers. Use per-document workflow concurrency and global worker concurrency.

Use stable classification batches defined by `(run_id, chunk_id, start_local_index, end_local_index)`. Do not let workers scan the database with arbitrary `OFFSET/LIMIT` to discover work.

---

## 15. Configuration

Create typed settings and document every variable in `.env.example`.

Include at least:

```dotenv
APP_ENV=local
LOG_LEVEL=INFO
API_HOST=0.0.0.0
API_PORT=8080
DATABASE_URL=postgresql+asyncpg://pipeline:pipeline@postgres:5432/pipeline
TEMPORAL_ADDRESS=temporal:7233
TEMPORAL_NAMESPACE=default
TEMPORAL_WORKFLOW_TASK_QUEUE=document-workflows
TEMPORAL_EXTRACTION_TASK_QUEUE=extraction
TEMPORAL_CLASSIFICATION_TASK_QUEUE=classification
S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=document-pipeline
S3_REGION=us-east-1
MAX_SOURCE_BYTES=10485760
CHUNK_TARGET_CHARS=4000
CHUNK_OVERLAP_CHARS=250
EXTRACTION_INSERT_BATCH_SIZE=250
CLASSIFICATION_BATCH_SIZE=25
CLASSIFICATION_PERSIST_BATCH_SIZE=5
MAX_EXTRACTION_ACTIVITIES_PER_DOCUMENT=4
MAX_CLASSIFICATION_ACTIVITIES_PER_DOCUMENT=4
EXTRACTION_WORKER_CONCURRENCY=8
CLASSIFICATION_WORKER_CONCURRENCY=8
MOCK_EXTRACTOR_DELAY_MS=20
MOCK_CLASSIFIER_DELAY_MS=100
```

Use safe local defaults but never hard-code secrets in application modules.

---

## 16. Docker Compose and startup

### 16.1 `compose.yaml`

Requirements:

- health checks for PostgreSQL, Temporal, MinIO, and API;
- dependency ordering based on health, not only container start;
- persistent named volumes for PostgreSQL, Temporal where appropriate, and MinIO;
- one application image reused by API and workers;
- separate commands for each service;
- migration job runs before API/workers begin serving;
- exposed ports:
  - API `8080`;
  - Temporal UI `8088` or another documented non-conflicting port;
  - MinIO API/UI documented;
- worker services must restart automatically on failure in local demo mode.

### 16.2 `start.sh`

Implement an executable, idempotent script:

```bash
#!/usr/bin/env bash
set -euo pipefail

docker compose up --build -d
./scripts/wait-for-services.sh
printf 'API: http://localhost:8080\n'
printf 'Temporal UI: http://localhost:8088\n'
```

The evaluator must be able to start everything with:

```bash
./start.sh
```

Also provide:

```bash
make up
make down
make logs
make migrate
make test
make integration-test
make demo
make lint
```

---

## 17. Test documents

Create original, realistic text; do not copy copyrighted articles.

### `test_documents/small.txt`

- business-style paragraph;
- 5–10 detectable entities;
- includes at least one person, company, address, and date.

### `test_documents/medium.txt`

- press-release or business-report style;
- 20–50 detectable entities;
- several paragraphs and at least two logical pages using `\f` if practical;
- includes ambiguous/unknown examples.

### `test_documents/large.txt`

- 100+ detectable entities;
- generated or hand-composed from original business records/announcements;
- spans enough text to create multiple extraction chunks and many classification batches;
- deterministic content so tests can assert minimum counts.

Provide `scripts/generate_large_document.py` so the large file can be recreated deterministically.

---

## 18. Tests

### 18.1 Unit tests

Cover at least:

- request validation;
- chunk boundaries, overlap, and canonical ownership;
- extractor offsets and position metadata;
- classifier mapping/confidence/reasoning;
- cursor encoding/decoding;
- service behavior and domain errors;
- duration calculation;
- idempotent token completion;
- run state-transition guards;
- full-rerun active-pointer behavior.

Use fakes for repository and provider interfaces in unit tests. Do not mock the unit under test.

### 18.2 Repository tests

Against PostgreSQL, verify:

- constraints and indexes exist;
- concurrent run-version creation does not create duplicate versions;
- extraction upserts do not duplicate tokens;
- duplicate classification completion does not increment progress twice;
- filtered token queries work by document/run/classification/page;
- active-run publication is atomic.

### 18.3 Integration tests

Integration tests must run against the Docker Compose stack and cover all assignment scenarios:

1. **Happy path**
   - submit small document;
   - wait for completion;
   - assert token results through API.
2. **Progress visibility**
   - submit large document with mock delays;
   - poll status;
   - observe at least one intermediate `CLASSIFYING` response with `0 < processed_count < total_tokens`.
3. **Partial rerun / crash recovery**
   - submit large document;
   - wait until at least several tokens are completed;
   - stop the classification worker;
   - verify persisted count does not reset;
   - restart the worker;
   - assert the same run completes and completed tokens were not double-counted.
4. **Full rerun**
   - complete one document;
   - rerun with changed content;
   - verify old active result remains during processing;
   - verify active run switches after completion;
   - verify default token queries contain only the new result.
5. **Concurrent documents**
   - submit small, medium, and large documents concurrently;
   - assert all complete independently.
6. **Token query filters**
   - filter by document, classification, page, and at least one additional supported field.
7. **Temporary dependency failure where practical**
   - demonstrate or test retry behavior for a transient repository/object-store error using a controlled fake at the activity/service level.

Tests must use bounded timeouts and print useful diagnostics on failure. Avoid arbitrary long sleeps; poll with deadlines.

---

## 19. Demo script

Create `scripts/demo.sh` and expose it as `make demo`. It must be safe, readable, and use:

```bash
set -euo pipefail
```

Prerequisites: Docker, Docker Compose, `curl`, and `jq`. The README must list them.

The script must demonstrate, in order:

### 19.1 Start and health

- start the stack if needed;
- wait for API readiness;
- show Temporal UI URL.

### 19.2 Happy path

- submit `small.txt` using the required `/process` endpoint;
- poll until complete;
- query `PERSON` tokens;
- print extraction and classification durations.

### 19.3 Real-time progress

- submit `large.txt` under a unique document ID;
- poll and print:

```text
status=CLASSIFYING processed=30 total=140
```

- show at least one intermediate progress value.

### 19.4 Partial recovery

- while the large document is classifying, wait until `processed_count >= 30` but less than total;
- run `docker compose stop classification-worker`;
- show status remains persisted;
- restart with `docker compose start classification-worker`;
- wait for completion;
- verify final processed count equals total and does not exceed it.

If multiple classification replicas are configured, the demo profile must use one replica so stopping it is deterministic.

### 19.5 Full rerun

- complete a document;
- capture its active run ID and token summary;
- call the full-rerun endpoint with changed text;
- show that the old active run remains visible while the new run is in progress;
- wait for completion;
- show that `active_run_id` changed and default token queries now return only the new run.

### 19.6 Concurrent documents

- submit the three sample documents concurrently;
- wait for all three;
- print final statuses.

### 19.7 Filtered token query

- query by `classification=PERSON`;
- query by page;
- print a concise JSON result.

The script must exit non-zero if any scenario fails.

---

## 20. README.md requirements

Write a complete reviewer-oriented `README.md` with this index:

1. Project overview
2. Architecture summary
3. Why Temporal, PostgreSQL, and MinIO
4. Repository structure
5. Prerequisites
6. Quick start
7. Configuration
8. API examples
9. Processing lifecycle
10. Partial recovery
11. Full rerun semantics
12. Progress and duration tracking
13. NLP and classifier interfaces
14. Test documents
15. Running tests and quality checks
16. Demo walkthrough
17. Failure handling and retry behavior
18. Known trade-offs and production follow-ups
19. AI-assisted development evidence

Include a compact Mermaid architecture diagram directly in the README.

The quick-start section must work as written:

```bash
cp .env.example .env
./start.sh
```

Include the exact assignment-compatible commands:

```bash
curl -X POST http://localhost:8080/process \
  -H 'Content-Type: application/json' \
  -d '{"document_id":"doc-123","text":"John Smith works at Acme Corp..."}'

curl http://localhost:8080/documents/doc-123/status

curl 'http://localhost:8080/documents/doc-123/tokens?classification=PERSON'
```

Document how to run the full demo:

```bash
make demo
```

Document how to inspect:

- Temporal UI;
- MinIO UI;
- API OpenAPI docs;
- application logs.

Be explicit that mock NLP and classifier adapters are deterministic and do not require API keys.

### Known trade-offs section

Briefly state:

- extraction must complete before classification, which simplifies exact progress but increases latency;
- bounded chunks need overlap and canonical ownership to handle cross-boundary entities;
- Temporal provides orchestration but is an additional service;
- mock NLP/LLM behavior demonstrates interfaces, not production model quality;
- exactly-once external classifier execution is not guaranteed, while persistence is idempotent;
- JSON text input is assignment-compatible, while true very-large uploads would normally use multipart or pre-signed object upload.

---

## 21. AI proficiency evidence

The assignment requires committed prompts and evidence of deliberate AI use.

- Copy this full specification to `docs/ai/prompts/001-poc-implementation.md`.
- Create `docs/ai/README.md` describing:
  - which parts were AI-assisted;
  - what the engineer reviewed manually;
  - commands used to validate generated code;
  - important corrections or design decisions made after AI output;
  - a statement that generated code was tested and remains the submitter's responsibility.
- Do not claim tests passed unless they were actually executed.
- Do not include secrets or personal data in prompt logs.

---

## 22. Resilience and observability

### 22.1 Structured logs

Every relevant log record should include available correlation fields:

- `request_id`;
- `document_id`;
- `run_id`;
- `workflow_id`;
- `chunk_id`;
- `batch_id`;
- `token_id`;
- `activity_attempt`.

Never log full source text, MinIO secrets, database credentials, or complete classifier prompts.

### 22.2 Retries and timeouts

- Configure HTTP/server timeouts sensibly.
- Configure database pool size and connection-recycle behavior.
- Use Temporal activity timeouts and retry policies explicitly.
- Add bounded backoff for readiness checks and demo polling.
- Avoid retry storms through bounded concurrency.

### 22.3 Graceful shutdown

Workers must stop accepting new work, allow in-flight activities to finish or heartbeat, and close clients. The API must close database and Temporal clients during lifespan shutdown.

### 22.4 Failure-state visibility

A failed run must expose:

- status `FAILED`;
- stable `error_code`;
- sanitized `error_detail`;
- timestamps and persisted progress up to failure.

Do not erase useful partial state automatically.

---

## 23. Security and validation baseline

This is a local POC, but implement basic hygiene:

- parameterized SQL through SQLAlchemy;
- no secrets committed;
- source-size limits;
- safe external document ID validation;
- no arbitrary object-store URI accepted directly from public API;
- no stack traces in client responses;
- pin dependencies in `uv.lock`;
- run containers as a non-root application user where practical;
- use separate local credentials from production assumptions.

Authentication is out of scope unless already present, but document that production would add it.

---

## 24. Acceptance criteria

The implementation is complete only when all items below are true.

### Functional

- [ ] `POST /process` returns 202 and starts asynchronous processing.
- [ ] Every extracted entity is stored in its own token row.
- [ ] Mock extraction returns text, NLP type, context, sentence/paragraph/page, and character offsets.
- [ ] Mock classification returns category, confidence, and reasoning.
- [ ] Status shows extraction progress and classification `processed_count / total_tokens`.
- [ ] Extraction and classification start/end timestamps are persisted.
- [ ] Durations are returned after completion.
- [ ] Partial recovery resumes the same run without resetting progress.
- [ ] Completed tokens are not reclassified or double-counted.
- [ ] Full rerun uses a new isolated run and atomically replaces the active result.
- [ ] Three documents can process concurrently.
- [ ] Token API filters by document, classification, page, and another field.

### Architecture and code quality

- [ ] API, extraction, and classification run as separate services/task queues.
- [ ] Controllers, models, validations, repositories, and services are clearly separated.
- [ ] Controllers contain no persistence or workflow business logic.
- [ ] Provider interfaces are clean and replaceable.
- [ ] Transactions and idempotency constraints are implemented.
- [ ] Large-work units are bounded.
- [ ] Configuration is environment-based.
- [ ] Logs are structured and correlated.
- [ ] Alembic migration creates the complete schema.

### Local setup and deliverables

- [ ] `./start.sh` starts the complete stack.
- [ ] `README.md` is complete and commands work as written.
- [ ] Small, medium, and large test documents exist with the required entity counts.
- [ ] Unit and integration tests cover required scenarios.
- [ ] `scripts/demo.sh` demonstrates all scenarios and fails on errors.
- [ ] AI prompts are committed under `docs/ai/prompts`.
- [ ] `ruff`, `mypy`, and `pytest` pass.

---

## 25. Suggested implementation order

Follow this order to reduce rework:

1. Initialize `pyproject.toml`, package layout, settings, logging, and quality tools.
2. Implement enums, ORM models, database session, and Alembic migration.
3. Implement repository interfaces and PostgreSQL repositories with repository tests.
4. Implement object-store interface and MinIO adapter.
5. Implement domain DTOs, mock extractor, mock classifier, and unit tests.
6. Implement services and validation schemas.
7. Implement API controllers and exception handlers.
8. Implement chunking and source-object lifecycle.
9. Implement Temporal activity contracts and activities.
10. Implement deterministic workflow and separate workers.
11. Implement Docker image, Compose stack, migrations, and startup scripts.
12. Create sample documents and generator.
13. Add unit/integration tests for all required scenarios.
14. Implement `scripts/demo.sh`.
15. Write and verify `README.md`.
16. Run all quality commands and the full demo from a clean checkout.

---

## 26. Final validation procedure

Before declaring the task complete, execute from a clean environment:

```bash
docker compose down -v --remove-orphans
cp .env.example .env
./start.sh
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run pytest tests/unit
uv run pytest tests/integration
make demo
```

Then verify:

- API docs load;
- Temporal UI shows completed workflows and retries during the recovery demo;
- MinIO contains immutable source and derived chunk objects;
- PostgreSQL counters match actual rows;
- stopping/restarting the classification worker resumes the same run;
- a full rerun changes `active_run_id` only after completion.

In the coding agent's final response, summarize:

- files created;
- architecture implemented;
- commands actually run;
- tests that passed;
- any known limitation that remains.

Do not state that a command passed unless it was executed successfully.