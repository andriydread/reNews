import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
)
from app.models.models import RefreshToken

router = APIRouter()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _cookie_params() -> dict:
    return {
        "httponly": True,
        "samesite": "lax",
        "secure": settings.ENVIRONMENT == "production",
    }


def _set_session_cookies(response: Response, access_token: str, refresh_token: str):
    params = _cookie_params()
    response.set_cookie(
        key="admin_access_token",
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **params,
    )
    response.set_cookie(
        key="admin_refresh_token",
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        **params,
    )


async def _store_refresh_token(db: AsyncSession, token: str, username: str) -> None:
    """Persist the SHA-256 of a refresh token; the raw value never hits the DB."""
    db.add(
        RefreshToken(
            token=hash_refresh_token(token),
            username=username,
            expires_at=_now_utc()
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Authenticates the admin and sets HttpOnly, Secure cookies for access and refresh tokens"""
    # Compare as UTF-8 bytes (str compare_digest raises TypeError on
    # non-ASCII input → 500), and evaluate BOTH comparisons unconditionally:
    # short-circuiting would skip the password check on a wrong username,
    # an observable difference that enables username enumeration.
    valid_user = secrets.compare_digest(
        username.encode(), settings.ADMIN_USER.encode()
    )
    valid_pass = secrets.compare_digest(
        password.encode(), settings.ADMIN_PASS.encode()
    )
    if not (valid_user & valid_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Opportunistic cleanup: expired rows would otherwise accumulate forever
    await db.execute(delete(RefreshToken).where(RefreshToken.expires_at < _now_utc()))

    access_token = create_access_token(data={"sub": username})
    refresh_token_str = create_refresh_token()
    await _store_refresh_token(db, refresh_token_str, username)
    await db.commit()

    _set_session_cookies(response, access_token, refresh_token_str)
    return {"message": "Login successful"}


@router.post("/refresh")
@limiter.limit("20/minute")
async def refresh(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    """Exchanges a valid refresh token for a new access token, rotating the refresh token"""
    refresh_token_str = request.cookies.get("admin_refresh_token")
    if not refresh_token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing"
        )

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == hash_refresh_token(refresh_token_str)
        )
    )
    db_token = result.scalar_one_or_none()

    if not db_token or db_token.expires_at < _now_utc():
        if db_token:
            await db.delete(db_token)
            await db.commit()
        # Build the 401 by hand: raising HTTPException makes FastAPI discard
        # the injected response, so delete_cookie on it never reaches the
        # browser and the stale cookie would be re-sent forever.
        error = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid or expired refresh token"},
        )
        error.delete_cookie("admin_refresh_token")
        error.delete_cookie("admin_access_token")
        return error

    # Rotation: the presented token is consumed, a fresh one replaces it —
    # a stolen refresh token stops working as soon as the owner uses theirs.
    await db.delete(db_token)
    new_refresh_token = create_refresh_token()
    await _store_refresh_token(db, new_refresh_token, db_token.username)
    await db.commit()

    new_access_token = create_access_token(data={"sub": db_token.username})
    _set_session_cookies(response, new_access_token, new_refresh_token)
    return {"message": "Token refreshed"}


@router.post("/logout")
async def logout(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    """Clears the admin session cookies and removes the refresh token from DB"""
    refresh_token_str = request.cookies.get("admin_refresh_token")
    if refresh_token_str:
        await db.execute(
            delete(RefreshToken).where(
                RefreshToken.token == hash_refresh_token(refresh_token_str)
            )
        )
        await db.commit()

    response.delete_cookie("admin_access_token")
    response.delete_cookie("admin_refresh_token")
    return {"message": "Logged out"}
