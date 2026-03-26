import asyncio

from app.core.database import engine
from app.models.article import Article  # noqa
from app.models.base import Base
from app.models.feed import Feed  # noqa


async def init_models():

    async with engine.begin() as conn:
        print("Dropping existing tables if any exist")
        await conn.run_sync(Base.metadata.drop_all)

        print("Creating tables")
        await conn.run_sync(Base.metadata.create_all)

        print("Done")


if __name__ == "__main__":
    asyncio.run(init_models())
