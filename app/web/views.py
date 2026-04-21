import jwt
from fastapi import APIRouter, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main dashboard page"""
    return templates.TemplateResponse(request=request, name="index.html")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page for admins"""
    return templates.TemplateResponse(request=request, name="login.html")


@router.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """Admin dashboard"""
    token = request.cookies.get("admin_access_token")
    authenticated = False
    if token:
        try:
            jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.ALGORITHM])
            authenticated = True
        except jwt.PyJWTError:
            pass

    if not authenticated:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    return templates.TemplateResponse(request=request, name="admin.html")
