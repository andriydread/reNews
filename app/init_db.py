import asyncio

from app.core.database import engine
from app.models.models import Base

# [!] [+] [✓] to use later
# ADD DB MIGRATIONS LATER


async def init_models():
    """Initializes the PostgreSQL database schema"""

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(init_models())
