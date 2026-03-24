"""JWT token creation and verification."""

import os
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt  # PyJWT library

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 120  # 2 hours per D-02
REFRESH_TOKEN_EXPIRE_DAYS = 30    # 30 days per D-02


def create_access_token(user_id: int, email: str, role: str) -> str:
    """Create a JWT access token with sub, email, role, exp, iat claims."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "type": "access",
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token_value() -> str:
    """Generate a cryptographically random refresh token string."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """SHA-256 hash of refresh token for DB storage (per D-01)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def verify_access_token(token: str) -> dict | None:
    """Verify and decode a JWT access token. Returns payload dict or None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def refresh_token_expires_at() -> datetime:
    """Return expiry datetime for a new refresh token."""
    return datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
