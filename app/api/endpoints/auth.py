import secrets

from fastapi import APIRouter, Form, HTTPException, Response, status

from app.core.config import settings
from app.core.security import create_access_token

router = APIRouter()


@router.post("/login")
async def login(
    response: Response, username: str = Form(...), password: str = Form(...)
):
    """Authenticates the admin and sets an HttpOnly, Secure cookie"""
    if not secrets.compare_digest(
        username, settings.ADMIN_USER
    ) or not secrets.compare_digest(password, settings.ADMIN_PASS):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    access_token = create_access_token(data={"sub": username})

    response.set_cookie(
        key="admin_access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=True if settings.ENVIRONMENT == "production" else False,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # settings is in minutes
    )
    return {"message": "Login successful"}


@router.post("/logout")
async def logout(response: Response):
    """Clears the admin session cookie"""
    response.delete_cookie("admin_access_token")
    return {"message": "Logged out"}
