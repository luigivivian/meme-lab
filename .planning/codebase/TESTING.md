# Testing Patterns

**Analysis Date:** 2026-03-30

## Test Framework

### Python Backend

**Runner:**
- pytest with `pytest-asyncio` (asyncio_mode = "auto")
- Config: `pyproject.toml` (`[tool.pytest.ini_options]`)
- HTTP client for integration tests: `httpx.AsyncClient` with `ASGITransport`

**Assertion Library:**
- pytest built-in `assert`
- `unittest.mock` (`AsyncMock`, `MagicMock`, `patch`)

**Run Commands:**
```bash
pytest                        # Run all tests
pytest tests/test_auth.py     # Run single file
pytest -v                     # Verbose output
pytest -k "test_register"     # Run by keyword
```

### Frontend (Next.js)

**Runner:**
- Vitest 4.x
- Config: `memelab/vitest.config.ts`
- Environment: jsdom
- Globals: enabled (no explicit import of `describe`, `it`, `expect` needed — but currently imported anyway)

**Assertion Library:**
- `@testing-library/jest-dom` (matchers)
- `@testing-library/react` (rendering)

**Run Commands:**
```bash
# From memelab/ directory
npx vitest                    # Run tests
npx vitest --watch            # Watch mode
npx vitest --coverage         # Coverage (not configured)
```

## Test File Organization

### Python

**Location:** `tests/` directory at project root — all tests co-located in flat structure, not mirrored alongside source files

**Naming:** `test_<feature>.py` (e.g., `test_auth.py`, `test_tenant.py`, `test_atomic_counter.py`)

**Structure:**
```
tests/
  __init__.py
  test_auth.py               # Auth endpoint integration tests
  test_tenant.py             # Repository-level isolation unit tests
  test_atomic_counter.py     # Usage counter unit + integration tests
  test_users_table.py        # ORM model structure tests
  test_preconditions.py      # CORS, health, log sanitizer tests
  test_manual_pipeline.py    # Image maker + content package tests
  test_key_selector.py
  test_api_usage.py
  test_static_fallback.py
  test_agents_quick.py
  test_legend_renderer.py
  test_legend_worker.py
  test_legend_config.py
  test_video_prompt_builder.py
  test_credits.py
  test_dashboard_metrics.py
  test_gemini_migration.py
```

### Frontend

**Location:** `memelab/src/__tests__/` — separate from source files

**Naming:** `<component-or-hook>.test.{ts,tsx}`

**Structure:**
```
memelab/src/__tests__/
  use-usage.test.ts           # Hook test stubs (all .todo)
  source-badges.test.tsx      # Component test stubs (all .todo)
  usage-widget.test.tsx       # Widget test stubs (all .todo)
```

**Status:** All frontend tests are `it.todo(...)` stubs — no implemented frontend tests exist.

## Test Structure

### Python — Integration Test Pattern (FastAPI + httpx)

```python
import os

# CRITICAL: Set env vars before importing app modules
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
    """Reset and init in-memory SQLite for each test."""
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


@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post("/auth/register", json={
        "email": "test@example.com",
        "password": "securepass123",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "test@example.com"
    assert "password" not in data
```

**Key patterns:**
- `setup_db` fixture is `autouse=True` — runs for every test without explicit use
- DB engine singletons are manually reset (`sess_mod._engine = None`) to ensure isolation
- In-memory SQLite (`sqlite+aiosqlite://`) for fast, self-contained tests
- `ASGITransport` runs the real FastAPI app without a live server

### Python — Repository Unit Test Pattern (mock session)

```python
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace

def _make_user(user_id: int, role: str = "user") -> SimpleNamespace:
    return SimpleNamespace(id=user_id, role=role, email=f"user{user_id}@test.com")

def _mock_session_for_scalar(character) -> AsyncMock:
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = character
    session.execute.return_value = result_mock
    return session

class TestForbidden:
    @pytest.mark.asyncio
    async def test_403_forbidden(self, regular_user, admin_character):
        session = _mock_session_for_scalar(admin_character)
        repo = CharacterRepository(session)
        with pytest.raises(PermissionError, match="forbidden"):
            await repo.get_by_slug("admin-char", user=regular_user)
```

### Python — Unit Test Pattern (no DB, no HTTP)

```python
def test_model_discovery_returns_list():
    from src.image_gen.gemini_client import discover_image_models

    mock_model_img = MagicMock()
    mock_model_img.name = "models/gemini-2.5-flash-image"

    mock_client = MagicMock()
    mock_client.models.list.return_value = [mock_model_img]

    with patch("src.image_gen.gemini_client._get_client", return_value=mock_client):
        result = discover_image_models()
    assert "gemini-2.5-flash-image" in result
```

### Frontend — Test Stub Pattern

```typescript
import { describe, it, expect } from "vitest";

describe("Usage Widget", () => {
  it.todo("renders usage card with service rows");
  it.todo("shows progress bar with emerald color when usage < 60%");
  it.todo("shows 'Ilimitado' for unlimited services (limit=0)");
});
```

## Mocking

**Framework:** `unittest.mock` (Python), vitest built-ins (frontend — not yet implemented)

**Python Mock Patterns:**

Mock an external SDK client:
```python
with patch("src.image_gen.gemini_client._get_client", return_value=mock_client):
    result = discover_image_models()
```

Mock SQLAlchemy async session for list queries:
```python
def _mock_session_for_list(characters: list) -> AsyncMock:
    session = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = characters
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    session.execute.return_value = result_mock
    return session
```

Mock SQLAlchemy async session for single-object queries:
```python
def _mock_session_for_scalar(character) -> AsyncMock:
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = character
    session.execute.return_value = result_mock
    return session
```

Lightweight domain objects without real ORM:
```python
from types import SimpleNamespace
user = SimpleNamespace(id=1, role="admin", email="user1@test.com")
character = SimpleNamespace(id=1, slug="char", user_id=1, is_deleted=False)
```

**What to Mock:**
- External API clients (`_get_client`, third-party SDKs)
- SQLAlchemy `AsyncSession` when testing repository logic in isolation
- Domain objects when testing access-control logic without a real DB

**What NOT to Mock:**
- The FastAPI app itself in integration tests — use `ASGITransport` with real `app`
- The database in integration tests — use in-memory SQLite instead
- `os.environ` — set real env vars before importing modules (see critical note below)

## Fixtures and Factories

**Shared helper functions** (not `@pytest.fixture`) for creating lightweight objects:

```python
def _make_user(user_id: int, role: str = "user") -> SimpleNamespace:
    return SimpleNamespace(id=user_id, role=role, email=f"user{user_id}@test.com")

def _make_character(char_id: int, slug: str, user_id: int) -> SimpleNamespace:
    return SimpleNamespace(id=char_id, slug=slug, user_id=user_id, is_deleted=False)
```

**Pytest fixtures** for shared test infrastructure:

```python
@pytest.fixture
def admin_user():
    return _make_user(1, role="admin")

@pytest.fixture
def regular_user():
    return _make_user(2, role="user")
```

**Auth helper** (reusable coroutine, not a fixture):
```python
async def _register_and_login(client: AsyncClient) -> tuple[str, int]:
    """Register a user and return (bearer_token, user_id)."""
    resp = await client.post("/auth/register", json={...})
    ...
    return f"Bearer {token}", user_id
```

**Location:**
- Test helpers are defined inline in the test file that uses them
- No shared `conftest.py` with cross-module fixtures (other than autouse `setup_db`)

## Coverage

**Requirements:** Not enforced — no coverage target configured in either pytest or vitest

**View Python Coverage:**
```bash
pytest --cov=src tests/
```

**View Frontend Coverage:**
```bash
npx vitest --coverage  # requires @vitest/coverage-v8
```

## Test Types

**Unit Tests (Python):**
- Scope: single function or class in isolation
- Approach: mock all dependencies, test one behavior per test
- Examples: `test_preconditions.py` (model discovery, log sanitizer), `test_tenant.py` (repo access control), `test_users_table.py` (ORM column assertions)

**Integration Tests (Python):**
- Scope: full HTTP request through real FastAPI app with in-memory SQLite
- Approach: `httpx.AsyncClient` + `ASGITransport` + autouse `setup_db` fixture
- Examples: `test_auth.py`, `test_atomic_counter.py` (endpoint sections)

**E2E Tests:**
- Not used (`.playwright-mcp/` directory exists but no test files found)

**Frontend Tests:**
- All stubs — not implemented

## Critical Notes

**Env var ordering is mandatory:** In Python tests that use `sqlite+aiosqlite://`, the env vars MUST be set before any import of `src.*` modules. Failure to do so causes the real database URL to be loaded at module import time, breaking in-memory isolation:
```python
import os
os.environ["SECRET_KEY"] = "test-secret-key-for-testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
# THEN import src modules:
from src.api.app import app
```

**Session singleton reset:** The `setup_db` fixture must reset `sess_mod._engine = None` and `sess_mod._session_factory = None` both before and after each test. Without this, engine state leaks between tests.

**asyncio_mode = "auto":** All async tests run automatically without needing `@pytest.mark.asyncio` in theory, but current test files still add it explicitly for clarity.

**Test class grouping:** Repository and access-control tests use `class Test<Scenario>:` to group related assertions under a named behavior (e.g., `TestUserIsolation`, `TestAdminBypass`, `TestForbidden`). Test functions inside classes still use `self` and `@pytest.mark.asyncio`.

## Common Patterns

**Boundary testing (limit at exact edge):**
```python
# Calls 1-5: allowed
for i in range(5):
    async with factory() as session:
        allowed, _ = await repo.check_limit(...)
        assert allowed is True, f"Call {i+1} should be allowed"
        await repo.increment(...)
        await session.commit()
# Call 6: rejected
async with factory() as session:
    allowed, _ = await repo.check_limit(...)
assert allowed is False, "Call 6 should be rejected"
```

**Env var override with restore:**
```python
old = os.environ.get("GEMINI_IMAGE_DAILY_LIMIT_FREE")
os.environ["GEMINI_IMAGE_DAILY_LIMIT_FREE"] = "5"
try:
    # ... test
finally:
    if old is None:
        os.environ.pop("GEMINI_IMAGE_DAILY_LIMIT_FREE", None)
    else:
        os.environ["GEMINI_IMAGE_DAILY_LIMIT_FREE"] = old
```

**Concurrent operation testing:**
```python
async def do_increment():
    async with factory() as session:
        await repo.increment(...)
        await session.commit()

await asyncio.gather(*[do_increment() for _ in range(10)])
```

**Security assertions (absence checks):**
```python
assert "password" not in data
assert "hashed_password" not in data
assert "AIzaSyD-test-key-1234567890abcdef" not in record.msg
```

---

*Testing analysis: 2026-03-30*
