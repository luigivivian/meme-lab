"""Tests for atomic usage counter (Phase 8 — QUOT-02, QUOT-03)."""

import asyncio
import os

# Set test env vars BEFORE importing app modules
os.environ["SECRET_KEY"] = "test-secret-key-for-testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.database.session import get_engine, get_session_factory, init_db
import src.database.session as sess_mod


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables in in-memory SQLite for each test."""
    sess_mod._engine = None
    sess_mod._session_factory = None
    await init_db()
    yield
    engine = get_engine()
    await engine.dispose()
    sess_mod._engine = None
    sess_mod._session_factory = None


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _register_and_login(client: AsyncClient) -> tuple[str, int]:
    """Register a user and return (bearer_token, user_id)."""
    resp = await client.post("/auth/register", json={
        "email": "counter@example.com",
        "password": "securepass123",
    })
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    resp = await client.post("/auth/login", json={
        "email": "counter@example.com",
        "password": "securepass123",
    })
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return f"Bearer {token}", user_id


# -- Repository unit tests ----------------------------------------------------


@pytest.mark.asyncio
async def test_single_increment():
    """UsageRepository.increment creates row with usage_count=1, then 2."""
    from src.database.repositories.usage_repo import UsageRepository

    factory = get_session_factory()
    async with factory() as session:
        repo = UsageRepository(session)
        count1 = await repo.increment(user_id=1, service="gemini_image", tier="free")
        await session.commit()
    assert count1 == 1

    async with factory() as session:
        repo = UsageRepository(session)
        count2 = await repo.increment(user_id=1, service="gemini_image", tier="free")
        await session.commit()
    assert count2 == 2


@pytest.mark.asyncio
async def test_concurrent_increments():
    """10 concurrent increment calls produce usage_count=10."""
    from src.database.repositories.usage_repo import UsageRepository

    async def do_increment():
        factory = get_session_factory()
        async with factory() as session:
            repo = UsageRepository(session)
            await repo.increment(user_id=1, service="gemini_image", tier="free")
            await session.commit()

    await asyncio.gather(*[do_increment() for _ in range(10)])

    # Verify final count
    factory = get_session_factory()
    async with factory() as session:
        repo = UsageRepository(session)
        count = await repo._get_current_count(
            user_id=1, service="gemini_image", tier="free",
            today_utc=repo._get_pt_today_start_utc(),
        )
    assert count == 10


@pytest.mark.asyncio
async def test_check_limit_under():
    """check_limit returns (True, ...) when no usage exists."""
    from src.database.repositories.usage_repo import UsageRepository

    factory = get_session_factory()
    async with factory() as session:
        repo = UsageRepository(session)
        allowed, info = await repo.check_limit(user_id=1, service="gemini_image", tier="free")
    assert allowed is True
    assert info["used"] == 0
    assert info["limit"] > 0
    assert info["remaining"] > 0
    assert "resets_at" in info


@pytest.mark.asyncio
async def test_check_limit_at_limit():
    """After 5 increments with limit=5, check_limit returns (False, ...)."""
    from src.database.repositories.usage_repo import UsageRepository

    old = os.environ.get("GEMINI_IMAGE_DAILY_LIMIT_FREE")
    os.environ["GEMINI_IMAGE_DAILY_LIMIT_FREE"] = "5"
    try:
        factory = get_session_factory()
        # Do 5 increments
        for _ in range(5):
            async with factory() as session:
                repo = UsageRepository(session)
                await repo.increment(user_id=1, service="gemini_image", tier="free")
                await session.commit()

        # 6th check should be rejected
        async with factory() as session:
            repo = UsageRepository(session)
            allowed, info = await repo.check_limit(user_id=1, service="gemini_image", tier="free")
        assert allowed is False
        assert info["used"] == 5
        assert info["limit"] == 5
        assert info["remaining"] == 0
    finally:
        if old is None:
            os.environ.pop("GEMINI_IMAGE_DAILY_LIMIT_FREE", None)
        else:
            os.environ["GEMINI_IMAGE_DAILY_LIMIT_FREE"] = old


@pytest.mark.asyncio
async def test_check_limit_rejected_row():
    """When check_limit rejects, a row with status='rejected' is inserted (D-03)."""
    from sqlalchemy import select
    from src.database.repositories.usage_repo import UsageRepository
    from src.database.models import ApiUsage

    old = os.environ.get("GEMINI_IMAGE_DAILY_LIMIT_FREE")
    os.environ["GEMINI_IMAGE_DAILY_LIMIT_FREE"] = "1"
    try:
        factory = get_session_factory()
        # Use 1 increment to hit limit
        async with factory() as session:
            repo = UsageRepository(session)
            await repo.increment(user_id=1, service="gemini_image", tier="free")
            await session.commit()

        # Trigger rejection
        async with factory() as session:
            repo = UsageRepository(session)
            allowed, _ = await repo.check_limit(user_id=1, service="gemini_image", tier="free")
            await session.commit()
        assert allowed is False

        # Verify rejected row
        async with factory() as session:
            result = await session.execute(
                select(ApiUsage).where(ApiUsage.status == "rejected")
            )
            rejected = result.scalars().all()
        assert len(rejected) >= 1
        assert rejected[0].service == "gemini_image"
    finally:
        if old is None:
            os.environ.pop("GEMINI_IMAGE_DAILY_LIMIT_FREE", None)
        else:
            os.environ["GEMINI_IMAGE_DAILY_LIMIT_FREE"] = old


@pytest.mark.asyncio
async def test_unlimited_when_zero():
    """With limit=0, check_limit always returns (True, ...) even after many increments."""
    from src.database.repositories.usage_repo import UsageRepository

    old = os.environ.get("GEMINI_IMAGE_DAILY_LIMIT_FREE")
    os.environ["GEMINI_IMAGE_DAILY_LIMIT_FREE"] = "0"
    try:
        factory = get_session_factory()
        # Increment 20 times
        for _ in range(20):
            async with factory() as session:
                repo = UsageRepository(session)
                await repo.increment(user_id=1, service="gemini_image", tier="free")
                await session.commit()

        # Should still be allowed
        async with factory() as session:
            repo = UsageRepository(session)
            allowed, info = await repo.check_limit(user_id=1, service="gemini_image", tier="free")
        assert allowed is True
        assert info["remaining"] == -1  # sentinel for unlimited
    finally:
        if old is None:
            os.environ.pop("GEMINI_IMAGE_DAILY_LIMIT_FREE", None)
        else:
            os.environ["GEMINI_IMAGE_DAILY_LIMIT_FREE"] = old


@pytest.mark.asyncio
async def test_get_user_usage():
    """get_user_usage returns UsageResponse-compatible dict with services list."""
    from src.database.repositories.usage_repo import UsageRepository

    factory = get_session_factory()
    # Increment gemini_image 3 times
    for _ in range(3):
        async with factory() as session:
            repo = UsageRepository(session)
            await repo.increment(user_id=1, service="gemini_image", tier="free")
            await session.commit()

    async with factory() as session:
        repo = UsageRepository(session)
        data = await repo.get_user_usage(user_id=1)

    assert "services" in data
    assert "resets_at" in data
    img_svc = next(s for s in data["services"] if s["service"] == "gemini_image")
    assert img_svc["used"] == 3
    assert img_svc["tier"] == "free"
    assert "limit" in img_svc
    assert "remaining" in img_svc


@pytest.mark.asyncio
async def test_get_daily_limit_from_env():
    """Setting env var overrides default limit."""
    from src.database.repositories.usage_repo import get_daily_limit

    old = os.environ.get("GEMINI_IMAGE_DAILY_LIMIT_FREE")
    os.environ["GEMINI_IMAGE_DAILY_LIMIT_FREE"] = "25"
    try:
        assert get_daily_limit("gemini_image", "free") == 25
    finally:
        if old is None:
            os.environ.pop("GEMINI_IMAGE_DAILY_LIMIT_FREE", None)
        else:
            os.environ["GEMINI_IMAGE_DAILY_LIMIT_FREE"] = old


@pytest.mark.asyncio
async def test_get_daily_limit_default():
    """get_daily_limit returns 15 for gemini_image free when env not set."""
    from src.database.repositories.usage_repo import get_daily_limit

    old = os.environ.pop("GEMINI_IMAGE_DAILY_LIMIT_FREE", None)
    try:
        assert get_daily_limit("gemini_image", "free") == 15
    finally:
        if old is not None:
            os.environ["GEMINI_IMAGE_DAILY_LIMIT_FREE"] = old


# -- Endpoint integration tests -----------------------------------------------


@pytest.mark.asyncio
async def test_usage_endpoint_returns_services(client):
    """GET /auth/me/usage returns 200 with services list and resets_at."""
    token, _ = await _register_and_login(client)
    resp = await client.get("/auth/me/usage", headers={"Authorization": token})
    assert resp.status_code == 200
    data = resp.json()
    assert "services" in data
    assert "resets_at" in data
    assert isinstance(data["services"], list)
    assert len(data["services"]) >= 1  # at least known services


@pytest.mark.asyncio
async def test_usage_endpoint_after_increments(client):
    """After incrementing 3 times, endpoint shows used=3 for gemini_image."""
    from src.database.repositories.usage_repo import UsageRepository

    token, user_id = await _register_and_login(client)

    # Increment via repository
    factory = get_session_factory()
    for _ in range(3):
        async with factory() as session:
            repo = UsageRepository(session)
            await repo.increment(user_id=user_id, service="gemini_image", tier="free")
            await session.commit()

    resp = await client.get("/auth/me/usage", headers={"Authorization": token})
    assert resp.status_code == 200
    data = resp.json()
    img_svc = next(s for s in data["services"] if s["service"] == "gemini_image")
    assert img_svc["used"] == 3


@pytest.mark.asyncio
async def test_usage_endpoint_unauthenticated(client):
    """GET /auth/me/usage without token returns 401 or 422."""
    resp = await client.get("/auth/me/usage")
    assert resp.status_code in (401, 422)


@pytest.mark.asyncio
async def test_rejection_response_format():
    """When limit reached, check_limit returns dict with required keys (D-02)."""
    from src.database.repositories.usage_repo import UsageRepository

    old = os.environ.get("GEMINI_IMAGE_DAILY_LIMIT_FREE")
    os.environ["GEMINI_IMAGE_DAILY_LIMIT_FREE"] = "1"
    try:
        factory = get_session_factory()
        async with factory() as session:
            repo = UsageRepository(session)
            await repo.increment(user_id=1, service="gemini_image", tier="free")
            await session.commit()

        async with factory() as session:
            repo = UsageRepository(session)
            allowed, info = await repo.check_limit(user_id=1, service="gemini_image", tier="free")
            await session.commit()

        assert allowed is False
        assert "used" in info
        assert "limit" in info
        assert "remaining" in info
        assert "resets_at" in info
        assert info["remaining"] == 0
    finally:
        if old is None:
            os.environ.pop("GEMINI_IMAGE_DAILY_LIMIT_FREE", None)
        else:
            os.environ["GEMINI_IMAGE_DAILY_LIMIT_FREE"] = old


@pytest.mark.asyncio
async def test_limit_enforcement_exactly_at_boundary():
    """With limit=5, calls 1-5 allowed, call 6 rejected (not 5th or 7th)."""
    from src.database.repositories.usage_repo import UsageRepository

    old = os.environ.get("GEMINI_IMAGE_DAILY_LIMIT_FREE")
    os.environ["GEMINI_IMAGE_DAILY_LIMIT_FREE"] = "5"
    try:
        factory = get_session_factory()

        # Calls 1-5: increment and check — all should be allowed
        for i in range(5):
            async with factory() as session:
                repo = UsageRepository(session)
                allowed, info = await repo.check_limit(user_id=1, service="gemini_image", tier="free")
                assert allowed is True, f"Call {i+1} should be allowed"
                await repo.increment(user_id=1, service="gemini_image", tier="free")
                await session.commit()

        # Call 6: should be rejected
        async with factory() as session:
            repo = UsageRepository(session)
            allowed, info = await repo.check_limit(user_id=1, service="gemini_image", tier="free")
            await session.commit()
        assert allowed is False, "Call 6 should be rejected"
        assert info["used"] == 5
    finally:
        if old is None:
            os.environ.pop("GEMINI_IMAGE_DAILY_LIMIT_FREE", None)
        else:
            os.environ["GEMINI_IMAGE_DAILY_LIMIT_FREE"] = old
