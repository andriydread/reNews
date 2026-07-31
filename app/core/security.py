import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, Request, status

from app.core.config import settings


def create_access_token(data: dict):
    """Generates a JWT token for admin access"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.ALGORITHM)


def create_refresh_token():
    """Generates a secure random refresh token"""
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """
    Refresh tokens are stored as SHA-256 hashes: read access to the DB must
    not be worth 30 days of admin access. The raw token exists only in the
    cookie; sha256 is fine here because the input is 64 random bytes
    (unbruteforceable), unlike a human password.
    """
    return hashlib.sha256(token.encode()).hexdigest()


def authenticated_admin(request: Request) -> str | None:
    """
    The single JWT-validation path: returns the admin username from the
    'admin_access_token' cookie, or None if the token is missing/invalid/
    expired or the subject isn't the configured admin.
    """
    token = request.cookies.get("admin_access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None
    if payload.get("sub") != settings.ADMIN_USER:
        return None
    return payload["sub"]


def verify_admin(request: Request) -> str:
    """
    Dependency to protect API routes: 401 unless a valid admin JWT cookie
    is present. Page routes use authenticated_admin() and redirect instead.
    """
    admin = authenticated_admin(request)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return admin
