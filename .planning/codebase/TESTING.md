# Testing Patterns

**Analysis Date:** 2026-03-23

## Test Framework

**Runner:**
- pytest (implied, standard for Python)
- Config: No `pytest.ini` or `pyproject.toml` with pytest section found
- Run with: `pytest tests/` or `python -m pytest`

**Assertion Library:**
- Python: assert statements (standard)
- Pytest fixtures not heavily used (straightforward class-based tests)

**Run Commands:**
```bash
pytest tests/                     # Run all tests
pytest tests/test_agents_quick.py # Single file
pytest tests/ -v                  # Verbose
pytest -m slow                    # Only tests marked @pytest.mark.slow
pytest -m "not slow"              # Skip slow tests (integration tests)
```

## Test File Organization

**Location:**
- Separate directory: `tests/` at project root
- NOT co-located with source code

**Current Test Files:**
- `tests/test_agents_quick.py` — Agent integration tests
- `tests/test_gemini_migration.py` — Historical (legacy)

**Naming Convention:**
- `test_[module].py` (e.g., `test_agents_quick.py`)

**Directory Structure:**
```
tests/
├── test_agents_quick.py        # Agent structure + availability + fetch
└── test_gemini_migration.py     # Legacy test
```

## Test Structure

**Suite Organization:**

```python
# Pattern from tests/test_agents_quick.py
import asyncio
import pytest
from src.pipeline.agents.bluesky_trends import BlueSkyTrendsAgent
from src.pipeline.models_v2 import TrendEvent, TrendSource

class TestAgentStructure:
    """Verifies agents inherit from AsyncSourceAgent."""

    def test_bluesky_herda_base(self):
        agent = BlueSkyTrendsAgent()
        assert isinstance(agent, AsyncSourceAgent)
        assert agent.name == "bluesky_trends"

class TestAgentAvailability:
    """Tests is_available() — async tests."""

    @pytest.mark.asyncio
    async def test_bluesky_disponivel(self):
        agent = BlueSkyTrendsAgent()
        assert await agent.is_available() is True

class TestAgentFetch:
    """Integration tests requiring network."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_bluesky_fetch_retorna_eventos(self):
        agent = BlueSkyTrendsAgent(max_posts=5)
        events = await agent.fetch()
        assert isinstance(events, list)
        for ev in events:
            assert isinstance(ev, TrendEvent)
            assert ev.source == TrendSource.BLUESKY
```

**Patterns Observed:**

1. **Class-based grouping:** Test methods organized into TestXxxxx classes by concern
2. **Descriptive names:** `test_bluesky_herda_base()` clearly states what's tested
3. **Setup/no teardown:** Agents instantiated in test methods (lightweight)
4. **Async markers:** `@pytest.mark.asyncio` for async functions
5. **Integration markers:** `@pytest.mark.slow` for network tests

## Mocking

**Framework:**
- Not used extensively (only 2 test files)
- Built-in unittest.mock available but not observed
- Tests prefer real objects when possible

**Patterns:**
- Tests instantiate real agents directly: `agent = BlueSkyTrendsAgent()`
- Network calls made (integration tests marked `@pytest.mark.slow`)
- No fixtures or mocking factories

**What to Mock:**
- API rate limiting (skip slow tests in CI)
- External service failures (optional)
- File I/O for large data

**What NOT to Mock:**
- Agent internal logic (should test real behavior)
- Enum values (should be correct)
- Database queries (use real DB or test DB)
- Async utilities (asyncio is stable)

## Fixtures and Factories

**Test Data:**
- Minimal fixtures used
- Agents created fresh per test: `agent = BlueSkyTrendsAgent(max_posts=5)`
- No factory patterns observed

**Location:**
- Tests are standalone
- Would add `tests/conftest.py` for shared fixtures if expanded

**Example Pattern (if fixtures added):**
```python
# Hypothetical conftest.py
import pytest
from src.pipeline.agents.bluesky_trends import BlueSkyTrendsAgent

@pytest.fixture
def bluesky_agent():
    """Fixture for BlueSky agent."""
    return BlueSkyTrendsAgent(max_posts=5)

@pytest.fixture
async def sample_trend_events():
    """Fixture for sample TrendEvent list."""
    return [
        TrendEvent(
            source=TrendSource.BLUESKY,
            title="test title",
            score=0.8,
            category="humor",
            url="https://...",
            metadata={},
            timestamp=datetime.now(),
        )
    ]
```

## Coverage

**Requirements:**
- None enforced (no coverage config detected)
- No CI/CD pipeline checking coverage

**Current Coverage:**
- Only agents tested (6% of codebase estimated)
- Critical paths untested: workers, processors, API routes, database queries

**If Adding Coverage:**
```bash
# Install pytest-cov
pip install pytest-cov

# Generate report
pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html
```

## Test Types

**Unit Tests:**
- Scope: Single agent/function in isolation
- Approach: Instantiate object, call method, assert result
- Example: `test_bluesky_herda_base()` — checks inheritance
- No external dependencies (structure tests)

**Integration Tests:**
- Scope: Agent fetching real data from API
- Approach: Call network-enabled methods, assert data structure
- Marked: `@pytest.mark.slow` (skipped in fast CI runs)
- Example: `test_bluesky_fetch_retorna_eventos()` — makes real API call

**E2E Tests:**
- Framework: Not used
- Would be needed for: full pipeline runs, database migrations, API acceptance tests
- Recommended: Add `tests/test_pipeline_e2e.py` for critical workflows

## Common Patterns

**Async Testing:**

```python
@pytest.mark.asyncio
async def test_bluesky_disponivel(self):
    agent = BlueSkyTrendsAgent()
    result = await agent.is_available()
    assert result is True

# Parallel async tests:
@pytest.mark.asyncio
@pytest.mark.slow
async def test_todos_agents_em_paralelo(self):
    agents = [BlueSkyTrendsAgent(), HackerNewsAgent()]
    results = await asyncio.gather(
        *[a.fetch() for a in agents],
        return_exceptions=True,  # Don't fail on first error
    )
    for result in results:
        assert not isinstance(result, Exception)
        assert isinstance(result, list)
```

**Data Structure Validation:**

```python
def test_bluesky_fetch_retorna_eventos(self):
    agent = BlueSkyTrendsAgent(max_posts=5)
    events = await agent.fetch()

    for ev in events:
        assert isinstance(ev, TrendEvent)        # Type check
        assert ev.source == TrendSource.BLUESKY  # Enum value
        assert ev.title                           # Non-empty
        assert 0.0 <= ev.score <= 1.0            # Range validation
        assert ev.category == "humor"             # Specific value
```

**Error Handling:**

```python
@pytest.mark.asyncio
async def test_agent_handles_network_error(self):
    # Should not raise, should return empty list or handle gracefully
    agent = SomeAgent(timeout=0.1)
    events = await agent.fetch()
    assert isinstance(events, list)  # Even if empty
    # No exception raised
```

## Testing Strategy Going Forward

**Critical Gaps:**
1. **Workers untested:** `phrase_worker.py`, `image_worker.py`, `post_production.py`
2. **Processors untested:** `analyzer.py`, `generator.py`, `aggregator.py`
3. **API routes untested:** All 50+ endpoints need integration tests
4. **Database untested:** CRUD operations, migrations, constraints
5. **Orchestrator untested:** L1→L5 flow, layer transitions

**Recommended Test Coverage:**

| Module | Type | Priority | Est. Tests |
|--------|------|----------|-----------|
| `src/database/repositories/*` | Unit | HIGH | 8 tests |
| `src/api/routes/*` | Integration | HIGH | 12 tests |
| `src/pipeline/workers/*` | Unit | HIGH | 6 tests |
| `src/pipeline/processors/*` | Unit | MEDIUM | 4 tests |
| `src/image_gen/gemini_client.py` | Unit | MEDIUM | 3 tests |
| Full pipeline run | E2E | MEDIUM | 2 tests |

**Recommended Additions:**

1. **Repository Tests (`tests/test_database.py`):**
```python
@pytest.mark.asyncio
async def test_character_repo_create():
    # Create character via repo
    # Assert fields saved correctly
    # Assert relationships intact
```

2. **API Integration Tests (`tests/test_api_routes.py`):**
```python
@pytest.mark.asyncio
async def test_pipeline_run_endpoint():
    # POST /pipeline/run
    # Assert response shape
    # Assert database updated
```

3. **Worker Tests (`tests/test_workers.py`):**
```python
def test_phrase_worker_generates_phrases():
    # Create work order
    # Call phrase_worker
    # Assert phrases generated and in database
```

## CI/CD Integration

**Current State:**
- No GitHub Actions or CI pipeline detected
- No `.github/workflows/` directory

**Recommended Setup:**

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.14'
      - run: pip install -r requirements.txt pytest pytest-asyncio
      - run: pytest tests/ -m "not slow"  # Skip slow tests in CI
```

---

*Testing analysis: 2026-03-23*
