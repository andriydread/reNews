import asyncio

from app.core.database import engine
from app.models.models import Base

# [!] [+] [✓] to use later


async def init_models():
    """Initializes the PostgreSQL database schema"""

    async with engine.begin() as conn:
        # -----ONLY FOR DEVELOPMENT, DELTE LATER
        # print("Dropping existing tables")
        # await conn.run_sync(Base.metadata.drop_all)
        # -----

        print("Creating tables from SQLAlchemy models")
        await conn.run_sync(Base.metadata.create_all)

        print("Database initialization complete")


if __name__ == "__main__":
    asyncio.run(init_models())
