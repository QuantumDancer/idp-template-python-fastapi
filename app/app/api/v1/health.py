from fastapi import APIRouter, Response

from app.schemas import HealthResponse, ReadinessResponse

health_router = APIRouter()


@health_router.get("/live", response_model=HealthResponse)
async def liveness() -> HealthResponse:
    """Kubernetes liveness probe.

    Returns 200 immediately with no external calls. If the process is running,
    it's alive. Kubernetes restarts the pod when this probe fails.
    """
    return HealthResponse(status="ok")


@health_router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
)
async def readiness(response: Response) -> ReadinessResponse:
    """Kubernetes readiness probe.

    Runs dependency checks and returns 503 if any fail, causing the pod to be
    removed from the load balancer until it recovers.

    Add checks for your dependencies:

        checks["database"] = await check_db()  # returns "ok" or an error string
        checks["cache"] = await check_redis()
    """
    checks: dict[str, str] = {}

    all_ok = all(v == "ok" for v in checks.values()) if checks else True

    if not all_ok:
        response.status_code = 503

    return ReadinessResponse(status="ok" if all_ok else "degraded", checks=checks)
