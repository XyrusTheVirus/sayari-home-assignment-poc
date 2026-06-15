"""HTTP controllers for starting processing."""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from document_pipeline.api.dependencies import get_processing_service
from document_pipeline.api.validations.process_requests import ProcessRequest
from document_pipeline.api.validations.process_responses import ProcessResponse
from document_pipeline.services.processing_service import ProcessingService

router = APIRouter(tags=["processing"])


@router.post("/process", response_model=ProcessResponse, status_code=status.HTTP_202_ACCEPTED)
@router.post("/api/v1/process", response_model=ProcessResponse, status_code=status.HTTP_202_ACCEPTED)
async def process_document(
    payload: ProcessRequest,
    request: Request,
    service: ProcessingService = Depends(get_processing_service),
) -> ProcessResponse:
    """Validate source size and delegate processing startup to the service layer."""

    max_source_bytes = request.app.state.settings.max_source_bytes
    if len(payload.text.encode("utf-8")) > max_source_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="source text is too large")
    result = await service.start(payload.document_id, payload.text)
    return ProcessResponse(**result.__dict__)
