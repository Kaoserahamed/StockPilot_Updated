"""Audit trail endpoint (FR-27).

Extracted from ``app/main.py`` so the HTTP surface of the application is
declared entirely under ``app/api/`` - ``main.py`` is then limited to wiring
(middleware, routers, lifespan) as described in ``docs/ARCHITECTURE.md``.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import Context, get_current_context
from app.db.session import get_db
from app.models.inventory import AuditLog

router = APIRouter(prefix="/audit-logs", tags=["audit"])


class AuditLogOut(BaseModel):
    """One recorded mutation, newest first."""

    id: int
    user_id: int | None = None
    action: str
    resource: str
    resource_id: str | None = None
    old_value: str | None = None
    new_value: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(
    ctx: Context = Depends(get_current_context),
    db: Session = Depends(get_db),
    action: str | None = None,
    resource: str | None = None,
    limit: int = Query(200, ge=1, le=1000),
):
    """FR-27.1/27.2: review who changed what, filterable by action or resource.

    Tenant-scoped: a business never sees another tenant's trail. Access is
    restricted to Owner/Manager as required by FR-25.4.
    """
    if ctx.role not in ("Owner", "Manager"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    q = db.query(AuditLog).filter(AuditLog.business_id == ctx.business_id)
    if action:
        q = q.filter(AuditLog.action == action)
    if resource:
        q = q.filter(AuditLog.resource == resource)
    return q.order_by(AuditLog.id.desc()).limit(limit).all()
