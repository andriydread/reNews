import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.security import create_access_token, create_refresh_token
from app.models.models import RefreshToken

router = APIRouter()


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
    if not secrets.compare_digest(
        username, settings.ADMIN_USER
    ) or not secrets.compare_digest(password, settings.ADMIN_PASS):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token = create_access_token(data={"sub": username})
    refresh_token_str = create_refresh_token()
    
    # Use naive UTC for database compatibility if DateTime is not timezone-aware
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    # Save refresh token to DB
    new_refresh_token = RefreshToken(
        token=refresh_token_str, username=username, expires_at=expires_at
    )
    db.add(new_refresh_token)
    await db.commit()

    cookie_params = {
        "httponly": True,
        "samesite": "lax",
        "secure": True if settings.ENVIRONMENT == "production" else False,
    }

    response.set_cookie(
        key="admin_access_token",
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **cookie_params,
    )

    response.set_cookie(
        key="admin_refresh_token",
        value=refresh_token_str,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        **cookie_params,
    )

    return {"message": "Login successful"}


@router.post("/refresh")
async def refresh(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    """Exchanges a valid refresh token for a new access token"""
    refresh_token_str = request.cookies.get("admin_refresh_token")
    if not refresh_token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing"
        )

    # Check if token exists in DB and is not expired
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == refresh_token_str)
    )
    db_token = result.scalar_one_or_none()

    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    
    if not db_token or db_token.expires_at < now_naive:
        if db_token:
            await db.delete(db_token)
            await db.commit()
        response.delete_cookie("admin_refresh_token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token"
        )

    # Generate new access token
    new_access_token = create_access_token(data={"sub": db_token.username})

    response.set_cookie(
        key="admin_access_token",
        value=new_access_token,
        httponly=True,
        samesite="lax",
        secure=True if settings.ENVIRONMENT == "production" else False,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    return {"message": "Token refreshed"}


@router.post("/logout")
async def logout(
    request: Request, response: Response, db: AsyncSession = Depends(get_db)
):
    """Clears the admin session cookies and removes the refresh token from DB"""
    refresh_token_str = request.cookies.get("admin_refresh_token")
    if refresh_token_str:
        await db.execute(delete(RefreshToken).where(RefreshToken.token == refresh_token_str))
        await db.commit()

    response.delete_cookie("admin_access_token")
    response.delete_cookie("admin_refresh_token")
    return {"message": "Logged out"}
