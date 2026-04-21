from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import FeedCreate, FeedResponse
from app.core.database import get_db
from app.core.security import verify_admin
from app.models.models import Feed

router = APIRouter()


@router.get("", response_model=list[FeedResponse])
async def get_feeds(
    session: AsyncSession = Depends(get_db), admin: str = Depends(verify_admin)
):
    """Returns a list of all managed RSS feeds."""
    result = await session.execute(select(Feed).order_by(Feed.title))
    return result.scalars().all()


@router.post("", response_model=FeedResponse)
async def add_feed(
    feed: FeedCreate,
    session: AsyncSession = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """Adds a new RSS feed source."""
    new_feed = Feed(title=feed.title.strip(), url=feed.url.strip())
    session.add(new_feed)
    try:
        await session.commit()
        await session.refresh(new_feed)
        return new_feed
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A feed with this URL already exists.",
        )


@router.delete("/{feed_id}")
async def delete_feed(
    feed_id: int,
    session: AsyncSession = Depends(get_db),
    admin: str = Depends(verify_admin),
):
    """Removes a feed and all its associated articles."""
    feed = await session.get(Feed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    await session.delete(feed)
    await session.commit()
    return {"message": "Feed deleted successfully"}
