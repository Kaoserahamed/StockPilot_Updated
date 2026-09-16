from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.error_tracking import bind_actor
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserBusiness

bearer = HTTPBearer(auto_error=False)


def _auth_failed(detail: str = "Not authenticated"):
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if creds is None or not creds.credentials:
        raise _auth_failed()
    try:
        user_id = decode_token(creds.credentials, expected_type="access")
    except ValueError:
        raise _auth_failed("Invalid or expired token") from None
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_active:
        raise _auth_failed("User inactive or not found")
    return user


class Context:
    """Authenticated user + resolved business membership (FR-24/FR-25)."""

    def __init__(self, user: User, business_id: int, role: str):
        self.user = user
        self.business_id = business_id
        self.role = role


from fastapi import Header  # noqa: E402


def get_current_context(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_business_id: int | None = Header(default=None, alias="X-Business-Id"),
) -> Context:
    q = db.query(UserBusiness).filter(
        UserBusiness.user_id == user.id, UserBusiness.is_active.is_(True)
    )
    memberships = q.all()
    if not memberships:
        raise HTTPException(status_code=403, detail="No active business membership")
    membership = None
    if x_business_id is not None:
        membership = next((m for m in memberships if m.business_id == x_business_id), None)
        if membership is None:
            raise HTTPException(status_code=403, detail="No access to this business")
    else:
        membership = memberships[0]
    # Bind the resolved actor so error reports and logs carry tenant + user.
    # Also mirror it onto the tracker snapshot: ``bind_actor`` writes a fresh
    # ContextVar dict that the middleware resets on exit, while the tracker
    # keeps ``last_route`` for post-response correlation.
    bind_actor(user_id=user.id, business_id=membership.business_id)
    try:
        from app.core.error_tracking import get_error_tracker as _get_tracker

        _trk = _get_tracker()
        _actor = dict(_trk.last_route) if isinstance(_trk.last_route, dict) else {}
        _actor.update({"user_id": user.id, "business_id": membership.business_id})
        _trk.last_route = _actor
    except Exception:
        pass
    return Context(user=user, business_id=membership.business_id, role=membership.role)


def require_roles(*roles: str):
    def checker(ctx: Context = Depends(get_current_context)) -> Context:
        if ctx.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role permissions")
        return ctx

    return checker


def find_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(or_(User.email == username, User.phone == username)).first()
