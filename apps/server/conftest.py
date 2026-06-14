"""Root conftest: shared fixtures for tests/ and module tests under src/.

Env overrides must land before any worknexus import (Settings is lru_cached).
"""

import os

TEST_DATABASE_URL = os.environ.get(
    "WORKNEXUS_TEST_DATABASE_URL", "postgresql+asyncpg://worknexus:worknexus@localhost:5432/worknexus_test"
)
os.environ["WORKNEXUS_DATABASE_URL"] = TEST_DATABASE_URL
os.environ["WORKNEXUS_BCRYPT_ROUNDS"] = "4"

from collections.abc import AsyncGenerator  # noqa: E402
from types import SimpleNamespace  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine  # noqa: E402

import worknexus.modules.audit.models  # noqa: E402
import worknexus.modules.identity.models  # noqa: E402
import worknexus.modules.projects.models  # noqa: E402
import worknexus.modules.skills.models  # noqa: E402
import worknexus.modules.work_items.models  # noqa: E402
import worknexus.modules.workchat.models  # noqa: E402, F401
from worknexus.db import Base, get_db  # noqa: E402
from worknexus.modules.identity import service as identity_service  # noqa: E402
from worknexus.modules.identity.models import AIAgent, Tenant, User  # noqa: E402
from worknexus.modules.identity.schemas import SetupIn  # noqa: E402
from worknexus.modules.projects.models import Project  # noqa: E402

OWNER_EMAIL = "owner@example.com"
OWNER_PASSWORD = "owner-pass-123"

SETUP_PAYLOAD = {
    "workspaceName": "Test Workspace",
    "email": OWNER_EMAIL,
    "displayName": "Owner",
    "password": OWNER_PASSWORD,
}


@pytest.fixture(scope="session")
async def engine() -> AsyncGenerator[AsyncEngine]:
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db(engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """Function-scoped session inside a transaction that always rolls back."""
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, join_transaction_mode="create_savepoint", expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()


@pytest.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient]:
    from worknexus.main import app

    async def _override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
async def initialized(db: AsyncSession) -> SimpleNamespace:
    """Run the setup service; returns owner/tenant/project/agent plus the session token."""
    owner, issued = await identity_service.run_setup(
        db,
        SetupIn(workspace_name="Test Workspace", email=OWNER_EMAIL, display_name="Owner", password=OWNER_PASSWORD),
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
    tenant = (await db.execute(select(Tenant))).scalar_one()
    project = (await db.execute(select(Project))).scalar_one()
    agent = (await db.execute(select(AIAgent))).scalar_one()
    return SimpleNamespace(owner=owner, tenant=tenant, project=project, agent=agent, session=issued)


@pytest.fixture
async def owner_client(client: AsyncClient, initialized: SimpleNamespace) -> AsyncClient:
    """Authenticated client: logs in as the setup owner, cookie kept in the jar."""
    resp = await client.post("/api/v1/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD})
    assert resp.json()["code"] == 0
    return client


@pytest.fixture
async def member_user(db: AsyncSession, initialized: SimpleNamespace) -> User:
    user = User(
        tenant_id=initialized.tenant.id,
        email="member@example.com",
        display_name="Member",
        password_hash=await identity_service.hash_password("member-pass-123"),
        status="active",
    )
    db.add(user)
    await db.flush()
    return user
