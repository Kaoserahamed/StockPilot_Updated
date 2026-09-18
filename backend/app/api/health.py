"""Health check endpoints for StockPilot backend.

Provides:
- GET /health          - basic liveness probe (kept for docker/compose)
- GET /health/live     - Kubernetes-style liveness alias
- GET /health/ready    - readiness probe (DB connectivity)
- GET /health/detailed - full dependency + observability status
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.error_tracking import get_error_tracker
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness probe - always returns 200 if the process is running."""
    return {
        "status": "ok",
        "service": "stockpilot-api",
        "version": settings.release_version,
        "environment": settings.environment,
    }


@router.get("/health/live")
def health_live() -> dict:
    """Liveness alias used by orchestrators that expect a ``/live`` path."""
    return health()


@router.get("/health/ready", response_model=None)
def health_ready(db: Session = Depends(get_db)) -> dict | JSONResponse:
    """Readiness probe - verifies database connectivity."""
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "database": db_status},
        )
    return {"status": "ready", "database": db_status}


@router.get("/health/detailed")
def health_detailed(db: Session = Depends(get_db)) -> dict:
    """Detailed health status including dependencies and error tracking."""
    checks: dict = {"database": "unknown"}

    # Database check
    try:
        result = db.execute(text("SELECT 1"))
        row = result.scalar()
        checks["database"] = "connected" if row == 1 else "error"
    except Exception as exc:
        checks["database"] = f"error: {type(exc).__name__}"

    # Error-tracking surface: counters + last failures, so an operator can see
    # crash activity without opening a log aggregator.
    tracker = get_error_tracker()
    checks["error_tracking"] = tracker.status()
    checks["recent_errors"] = tracker.recent_reports(limit=5)

    # Overall status is driven by hard dependencies only; the error-tracking
    # block above is informational and must not flip the probe to "degraded".
    all_ok = checks["database"] == "connected"
    checks["status"] = "healthy" if all_ok else "degraded"

    return checks
