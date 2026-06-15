FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev || uv sync --no-dev

COPY alembic.ini compose.yaml ./
COPY migrations ./migrations
COPY scripts ./scripts
COPY test_documents ./test_documents

RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser
ENV PATH="/app/.venv/bin:${PATH}" PYTHONPATH=/app/src

CMD ["uvicorn", "document_pipeline.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
