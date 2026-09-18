"""JWT helpers and password hashing for StockPilot auth.

HS256 tokens are signed with ``SECRET_KEY`` (see ``app.core.config``); bcrypt
hashes passwords. PyJWT is the only JWT backend so the ecdsa/rsa/pyasn1 stack
pulled in by python-jose is not installed.
"""

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from jwt import InvalidTokenError

from app.core.config import settings


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    expire = datetime.now(UTC) + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "access"},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def create_refresh_token(subject: str) -> str:
    """Create a long-lived refresh token for obtaining new access tokens."""
    expire = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "refresh"},
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def decode_token(token: str, expected_type: str = "access") -> str:
    """Decode and validate a JWT token.

    Args:
        token: The JWT string to decode.
        expected_type: Either "access" or "refresh" — validates the token's
                       claim type matches what the caller expects.

    Raises:
        ValueError: If the token is invalid, expired, or type-mismatched.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        sub: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        if sub is None:
            raise InvalidTokenError("missing sub")
        if token_type != expected_type:
            raise InvalidTokenError(f"expected {expected_type} token, got {token_type}")
        return sub
    except InvalidTokenError as exc:
        raise ValueError("Invalid or expired token") from exc
