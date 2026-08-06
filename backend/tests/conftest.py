"""Shared test fixtures.

Environment is redirected to a dedicated test database and Redis DB *before* any
app module is imported, because get_settings() is lru_cache'd — the first call
wins for the whole run, so this has to happen at import time, above the app
imports below.
"""

import os

# --- environment redirection (must precede app imports) ----------------------

_DEV_DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://performance_eval:devpassword@postgres:5432/performance_eval"
)
_DB_BASE, _DEV_DB_NAME = _DEV_DB_URL.rsplit("/", 1)
# Idempotent: this module can be imported more than once in a run, and blindly
# re-appending the suffix would point at "<name>_test_test".
TEST_DB_NAME = _DEV_DB_NAME if _DEV_DB_NAME.endswith("_test") else f"{_DEV_DB_NAME}_test"
os.environ["DATABASE_URL"] = f"{_DB_BASE}/{TEST_DB_NAME}"

_DEV_REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
os.environ["REDIS_URL"] = f"{_DEV_REDIS_URL.rsplit('/', 1)[0]}/15"

os.environ["JWT_SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256"
# Blank on purpose: nothing in the suite may make a real Gemini call.
os.environ["GEMINI_API_KEY"] = ""
# Blank on purpose: nothing in the suite may make a real Resend call.
os.environ["RESEND_API_KEY"] = ""

# --- app imports -------------------------------------------------------------

import asyncpg  # noqa: E402
import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
from app.core.redis import redis_client  # noqa: E402
from app.core.security import create_access_token  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Company, EvaluationCycle, Question, User, UserRole  # noqa: E402
from app.models.question import QuestionType  # noqa: E402
from tests.factories import make_user  # noqa: E402


async def _ensure_test_database() -> None:
    """CREATE DATABASE can't run inside a transaction, so use a raw asyncpg connection."""
    admin_dsn = f"{_DB_BASE}/postgres".replace("postgresql+asyncpg://", "postgresql://")
    conn = await asyncpg.connect(admin_dsn)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB_NAME)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        await conn.close()


@pytest.fixture(scope="session")
async def db_engine():
    await _ensure_test_database()
    engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """One transaction per test, rolled back at the end.

    join_transaction_mode="create_savepoint" means the app's own db.commit() calls
    become savepoint releases instead of real commits, so the outer transaction can
    still roll everything back and tests stay isolated from each other.
    """
    connection = await db_engine.connect()
    transaction = await connection.begin()
    session_maker = async_sessionmaker(
        bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
    )
    session = session_maker()
    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest.fixture(autouse=True)
async def flush_redis():
    await redis_client.flushdb()
    yield
    await redis_client.flushdb()


@pytest.fixture
async def client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def as_user(client):
    """Authenticate the shared client as a given user.

    Mints a token directly rather than going through /auth/login — login is covered
    explicitly in test_auth.py, and every other test just needs *an* authenticated
    caller without paying for another bcrypt verify. Calling it again switches user.
    """

    def _as(user: User) -> AsyncClient:
        client.headers["Authorization"] = f"Bearer {create_access_token(str(user.id))}"
        return client

    return _as


# --- data fixtures -----------------------------------------------------------


@pytest.fixture
async def company(db_session) -> Company:
    c = Company(name="Acme Inc.")
    db_session.add(c)
    await db_session.flush()
    return c


@pytest.fixture
async def other_company(db_session) -> Company:
    c = Company(name="Globex Corp")
    db_session.add(c)
    await db_session.flush()
    return c


@pytest.fixture
async def super_admin(db_session) -> User:
    return await make_user(db_session, role=UserRole.SUPER_ADMIN, company_id=None)


@pytest.fixture
async def company_admin(db_session, company) -> User:
    return await make_user(db_session, role=UserRole.COMPANY_ADMIN, company_id=company.id)


@pytest.fixture
async def hr_user(db_session, company) -> User:
    return await make_user(db_session, role=UserRole.HR, company_id=company.id)


@pytest.fixture
async def manager(db_session, company) -> User:
    return await make_user(db_session, role=UserRole.MANAGER, company_id=company.id)


@pytest.fixture
async def employee(db_session, company, manager) -> User:
    """An employee who reports to `manager` — the shape activation fan-out needs."""
    return await make_user(db_session, role=UserRole.EMPLOYEE, company_id=company.id, manager_id=manager.id)


@pytest.fixture
async def other_company_admin(db_session, other_company) -> User:
    return await make_user(db_session, role=UserRole.COMPANY_ADMIN, company_id=other_company.id)


@pytest.fixture
async def cycle(db_session, company) -> EvaluationCycle:
    """A draft cycle with one rating and one text question."""
    from datetime import date

    c = EvaluationCycle(
        company_id=company.id, name="Q1 2026 Review", start_date=date(2026, 1, 1), end_date=date(2026, 3, 31)
    )
    db_session.add(c)
    await db_session.flush()
    db_session.add(Question(cycle_id=c.id, text="Rate overall performance", type=QuestionType.RATING, order=0))
    db_session.add(Question(cycle_id=c.id, text="What could improve?", type=QuestionType.TEXT, order=1))
    await db_session.flush()
    await db_session.refresh(c)
    return c
