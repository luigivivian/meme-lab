"""Integration tests for auth endpoints."""

import os

# Set test env vars BEFORE importing app modules
os.environ["SECRET_KEY"] = "test-secret-key-for-testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.app import app
from src.database.session import get_engine, init_db
import src.database.session as sess_mod


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create tables in in-memory SQLite for each test."""
    # Reset engine singleton for test DB
    sess_mod._engine = None
    sess_mod._session_factory = None

    await init_db()
    yield
    # Cleanup
    engine = get_engine()
    await engine.dispose()
    sess_mod._engine = None
    sess_mod._session_factory = None


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# -- Register tests -----------------------------------------------------------


@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "securepass123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "user"
    assert "password" not in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    await client.post("/auth/register", json={
        "email": "dup@example.com", "password": "securepass123"
    })
    resp = await client.post("/auth/register", json={
        "email": "dup@example.com", "password": "securepass123"
    })
    assert resp.status_code == 409


# -- Login tests --------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/auth/register", json={
        "email": "login@example.com", "password": "securepass123"
    })
    resp = await client.post("/auth/login", json={
        "email": "login@example.com", "password": "securepass123"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/auth/register", json={
        "email": "wrong@example.com", "password": "securepass123"
    })
    resp = await client.post("/auth/login", json={
        "email": "wrong@example.com", "password": "wrongpassword"
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_email(client):
    resp = await client.post("/auth/login", json={
        "email": "nobody@example.com", "password": "whatever123"
    })
    assert resp.status_code == 401


# -- Refresh tests ------------------------------------------------------------


@pytest.mark.asyncio
async def test_refresh_success(client):
    await client.post("/auth/register", json={
        "email": "refresh@example.com", "password": "securepass123"
    })
    login_resp = await client.post("/auth/login", json={
        "email": "refresh@example.com", "password": "securepass123"
    })
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post("/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["refresh_token"] != refresh_token  # rotated


@pytest.mark.asyncio
async def test_refresh_reuse_old_token(client):
    await client.post("/auth/register", json={
        "email": "reuse@example.com", "password": "securepass123"
    })
    login_resp = await client.post("/auth/login", json={
        "email": "reuse@example.com", "password": "securepass123"
    })
    old_refresh = login_resp.json()["refresh_token"]

    # Use it once (rotates)
    await client.post("/auth/refresh", json={"refresh_token": old_refresh})

    # Try old token again — should fail
    resp = await client.post("/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 401


# -- Logout tests -------------------------------------------------------------


@pytest.mark.asyncio
async def test_logout_success(client):
    await client.post("/auth/register", json={
        "email": "logout@example.com", "password": "securepass123"
    })
    login_resp = await client.post("/auth/login", json={
        "email": "logout@example.com", "password": "securepass123"
    })
    refresh_token = login_resp.json()["refresh_token"]

    resp = await client.post("/auth/logout", json={
        "refresh_token": refresh_token
    })
    assert resp.status_code == 200

    # Subsequent refresh should fail
    resp2 = await client.post("/auth/refresh", json={
        "refresh_token": refresh_token
    })
    assert resp2.status_code == 401


# -- Me endpoint tests --------------------------------------------------------


@pytest.mark.asyncio
async def test_me_success(client):
    await client.post("/auth/register", json={
        "email": "me@example.com", "password": "securepass123"
    })
    login_resp = await client.post("/auth/login", json={
        "email": "me@example.com", "password": "securepass123"
    })
    token = login_resp.json()["access_token"]

    resp = await client.get("/auth/me", headers={
        "Authorization": f"Bearer {token}"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "me@example.com"
    assert data["role"] == "user"


@pytest.mark.asyncio
async def test_me_no_token(client):
    resp = await client.get("/auth/me")
    assert resp.status_code in (401, 422)
