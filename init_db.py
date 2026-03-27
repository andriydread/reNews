import asyncio

from app.core.database import engine
from app.models.models import Base


async def init_models():

    async with engine.begin() as conn:
        print(
            "Dropping existing tables, only for development, comment after use and remove later"
        )
        await conn.run_sync(Base.metadata.drop_all)

        print("[+] Creating tables if not exist.")
        await conn.run_sync(Base.metadata.create_all)

        print("[->] Done")


if __name__ == "__main__":
    asyncio.run(init_models())
