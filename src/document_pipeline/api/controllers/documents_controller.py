"""HTTP controllers for document status, reruns, and token queries."""

from dataclasses import asdict
from uuid import UUID

from fastapi import APIRouter, Depends

from document_pipeline.api.dependencies import get_query_service, get_rerun_service
from document_pipeline.api.validations.common import StageProgressResponse, TokenItemResponse
from document_pipeline.api.validations.document_requests import RerunRequest, TokenQueryParams
from document_pipeline.api.validations.document_responses import (
    DocumentStatusResponse,
    StatusErrorResponse,
    TokenListResponse,
)
from document_pipeline.api.validations.process_responses import ProcessResponse
from document_pipeline.repositories.interfaces import TokenFilters
from document_pipeline.services.document_query_service import DocumentQueryService
from document_pipeline.services.rerun_service import RerunService

router = APIRouter(tags=["documents"])


@router.post(
    "/api/v1/documents/{document_id}/rerun", response_model=ProcessResponse, status_code=202
)
@router.post(
    "/api/v1/documents/{document_id}/runs", response_model=ProcessResponse, status_code=202
)
async def rerun_document(
    document_id: str,
    payload: RerunRequest,
    service: RerunService = Depends(get_rerun_service),
) -> ProcessResponse:
    """Create a new isolated processing run for a document."""

    result = await service.rerun(document_id, payload.text, payload.reuse_source)
    return ProcessResponse(**asdict(result))


@router.get("/documents/{document_id}/status", response_model=DocumentStatusResponse)
@router.get("/api/v1/documents/{document_id}/status", response_model=DocumentStatusResponse)
async def get_status(
    document_id: str,
    run_id: UUID | None = None,
    service: DocumentQueryService = Depends(get_query_service),
) -> DocumentStatusResponse:
    """Return latest or specific run status for a logical document."""

    status = await service.status(document_id, run_id)
    return DocumentStatusResponse(
        document_id=status.document_id,
        run_id=status.run_id,
        active_run_id=status.active_run_id,
        version=status.version,
        status=status.status,
        extraction=StageProgressResponse(
            completed_chunks=status.extraction.completed,
            total_chunks=status.extraction.total,
            started_at=status.extraction.started_at,
            completed_at=status.extraction.completed_at,
            duration_ms=status.extraction.duration_ms,
        ),
        classification=StageProgressResponse(
            processed_count=status.classification.completed,
            total_tokens=status.classification.total,
            started_at=status.classification.started_at,
            completed_at=status.classification.completed_at,
            duration_ms=status.classification.duration_ms,
        ),
        error=(
            StatusErrorResponse(code=status.error_code, detail=status.error_detail)
            if status.error_code is not None
            else None
        ),
    )


@router.get("/documents/{document_id}/tokens", response_model=TokenListResponse)
@router.get("/api/v1/documents/{document_id}/tokens", response_model=TokenListResponse)
async def list_tokens(
    document_id: str,
    params: TokenQueryParams = Depends(),
    service: DocumentQueryService = Depends(get_query_service),
) -> TokenListResponse:
    """Return active or historical tokens with filters and keyset pagination."""

    items, next_cursor = await service.tokens(
        document_id,
        TokenFilters(
            classification=params.classification,
            page_number=params.page_number,
            nlp_type=params.nlp_type,
            classification_status=params.classification_status,
        ),
        params.limit,
        params.cursor,
        params.run_id,
    )
    return TokenListResponse(
        items=[TokenItemResponse(**asdict(item)) for item in items], next_cursor=next_cursor
    )
