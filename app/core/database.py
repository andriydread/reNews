from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings

# Create the Database Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    # Settings for db to handle multiple background tasks at once
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    # Logs SQL queries for debugging
    echo=False if settings.ENVIRONMENT == "production" else True,
)

# Create the Session Factory
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


async def get_db():
    """
    Use this to get an active database session.
    Example: session = await anext(get_db())
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            # Makes sure that session is closed if error occurs
            await session.close()
