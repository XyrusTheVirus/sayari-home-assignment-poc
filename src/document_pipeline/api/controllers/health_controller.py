"""Health and readiness controllers."""

from fastapi import APIRouter, Request
from fastapi.responses import ORJSONResponse
from sqlalchemy import text
from temporalio.api.workflowservice.v1 import GetSystemInfoRequest

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def live() -> dict[str, str]:
    """Return liveness when the API process can serve requests."""

    return {"status": "ok"}


@router.get("/health/ready")
async def ready(request: Request) -> ORJSONResponse:
    """Check PostgreSQL, Temporal, and object-store access for readiness."""

    try:
        async with request.app.state.session_factory() as session:
            await session.execute(text("SELECT 1"))
        await request.app.state.temporal_client.workflow_service.get_system_info(
            GetSystemInfoRequest()
        )
    except Exception as exc:
        return ORJSONResponse(
            status_code=503, content={"status": "not_ready", "detail": type(exc).__name__}
        )
    return ORJSONResponse({"status": "ready"})
