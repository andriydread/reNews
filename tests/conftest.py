import os

from dotenv import load_dotenv

# Load the real .env (DB host/credentials for the compose Postgres), then
# override everything that must differ under test — BEFORE any app import:
# app.core.config builds its Settings singleton at import time, and real
# environment variables take precedence over the dotenv file.
load_dotenv()
os.environ["POSTGRES_DB"] = "renews_test"
os.environ["ENVIRONMENT"] = "development"
os.environ["ADMIN_USER"] = "testadmin"
os.environ["ADMIN_PASS"] = "testpass"
os.environ["JWT_SECRET"] = "test-secret-not-production-0123456789abcdef"

import asyncpg  # noqa: E402
import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import get_db  # noqa: E402
from app.models.models import Base  # noqa: E402
from main import app  # noqa: E402

TEST_DB = "renews_test"


@pytest.fixture(scope="session")
async def engine():
    """(Re)create the throwaway test database, build the schema once per run."""
    admin = await asyncpg.connect(
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        database="postgres",
    )
    await admin.execute(f'DROP DATABASE IF EXISTS "{TEST_DB}"')
    await admin.execute(f'CREATE DATABASE "{TEST_DB}"')
    await admin.close()

    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(engine):
    """Transaction-rollback isolation: everything a test writes is rolled back.

    The session joins an outer transaction via savepoints, so application code
    can call commit() freely without anything reaching the database for real.
    """
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest.fixture
async def client(db_session):
    """HTTP client against the app, wired to the test session.

    ASGITransport does not run lifespan events, so the APScheduler worker in
    main.py never starts under test.
    """

    async def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    # /login is rate-limited 5/minute by client IP; the suite exceeds that.
    app.state.limiter.enabled = False
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_client(client):
    """A client that has logged in as the test admin (cookies set)."""
    resp = await client.post(
        "/api/auth/login",
        data={"username": "testadmin", "password": "testpass"},
    )
    assert resp.status_code == 200, resp.text
    return client
