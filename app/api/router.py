from fastapi import APIRouter

from app.api.endpoints import articles, auth, feeds

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(articles.router, prefix="/articles", tags=["articles"])
api_router.include_router(feeds.router, prefix="/feeds", tags=["feeds"])
