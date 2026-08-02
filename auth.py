"""
auth.py — JWT + bcrypt authentication helpers for Aethel ATS
─────────────────────────────────────────────────────────────
Uses PyJWT for token encoding and bcrypt for password hashing.
Tokens are stateless JWTs — no server-side session storage needed.

Env vars:
  JWT_SECRET   — HMAC-SHA256 signing secret (required in prod)
  JWT_EXP_DAYS — access token lifetime in days (default: 7)
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

try:
    import bcrypt
except ImportError:
    print("[Auth] WARNING: bcrypt not installed. Run: pip install bcrypt", file=sys.stderr)
    bcrypt = None  # type: ignore

try:
    import jwt
except ImportError:
    print("[Auth] WARNING: PyJWT not installed. Run: pip install PyJWT", file=sys.stderr)
    jwt = None  # type: ignore

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from database import get_user_by_id

# ─── Config ──────────────────────────────────────────────────
_JWT_SECRET = os.environ.get("JWT_SECRET", "aethel-dev-secret-change-in-production")
_JWT_ALGORITHM = "HS256"
_JWT_EXP_DAYS = int(os.environ.get("JWT_EXP_DAYS", "7"))

_bearer_scheme = HTTPBearer(auto_error=False)


# ─── Password helpers ─────────────────────────────────────────
def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt. Returns the hash as a UTF-8 string."""
    if bcrypt is None:
        raise RuntimeError("bcrypt library not installed")
    hashed = bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plain matches the stored bcrypt hash."""
    if bcrypt is None:
        raise RuntimeError("bcrypt library not installed")
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ─── JWT helpers ──────────────────────────────────────────────
def create_access_token(user_id: int, email: str, role: str) -> str:
    """
    Create a signed JWT access token.
    Payload: sub (user_id), email, role, exp (expiry), iat (issued-at).
    """
    if jwt is None:
        raise RuntimeError("PyJWT library not installed")
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + timedelta(days=_JWT_EXP_DAYS),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """
    Decode and validate a JWT. Returns payload dict or None on failure.
    Raises nothing — caller must check for None.
    """
    if jwt is None:
        return None
    try:
        payload = jwt.decode(token, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
        return payload
    except Exception:
        return None


# ─── FastAPI dependency ───────────────────────────────────────
async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
):
    """
    FastAPI dependency. Extracts and validates the Bearer token.
    Returns the User ORM object.
    Raises HTTP 401 on missing/invalid token.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = int(payload.get("sub", 0))
    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
):
    """
    Like get_current_user but does NOT raise on missing token.
    Returns User or None. Use this on endpoints that work for both
    authenticated and anonymous users (e.g. /analyze).
    """
    if credentials is None:
        return None
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None
    user_id = int(payload.get("sub", 0))
    return get_user_by_id(user_id)
