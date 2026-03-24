"""Tests for UsageAwareKeySelector (Phase 9 — QUOT-04, QUOT-05)."""

import os

# Set test env vars BEFORE importing app modules
os.environ["GOOGLE_API_KEY"] = "test-free-key"
os.environ["GOOGLE_API_KEY_PAID"] = "test-paid-key"
os.environ.pop("GEMINI_FORCE_TIER", None)

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.key_selector import KeyResolution, UsageAwareKeySelector


@pytest.fixture
def mock_session():
    """Fake AsyncSession — never actually used by the selector."""
    return MagicMock()


@pytest.fixture
def selector():
    """Default selector with both keys configured."""
    return UsageAwareKeySelector()


# --------------------------------------------------------------------------
# 1. Auto mode: free key when under limit
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_returns_free_when_under_limit(selector, mock_session):
    """When check_limit allows, resolve returns free key with mode=auto."""
    mock_check = AsyncMock(return_value=(True, {
        "used": 5, "limit": 15, "remaining": 10,
        "resets_at": "2026-03-25T00:00:00-07:00",
    }))
    with patch("src.services.key_selector.UsageRepository") as MockRepo:
        MockRepo.return_value.check_limit = mock_check
        result = await selector.resolve(user_id=1, session=mock_session)

    assert result.api_key == "test-free-key"
    assert result.tier == "gemini_free"
    assert result.mode == "auto"
    mock_check.assert_awaited_once_with(1, "gemini_image", "free")


# --------------------------------------------------------------------------
# 2. Auto mode: paid key when over limit
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_returns_paid_when_over_limit(selector, mock_session):
    """When check_limit rejects, resolve returns paid key with mode=auto."""
    mock_check = AsyncMock(return_value=(False, {
        "used": 15, "limit": 15, "remaining": 0,
        "resets_at": "2026-03-25T00:00:00-07:00",
    }))
    with patch("src.services.key_selector.UsageRepository") as MockRepo:
        MockRepo.return_value.check_limit = mock_check
        result = await selector.resolve(user_id=1, session=mock_session)

    assert result.api_key == "test-paid-key"
    assert result.tier == "gemini_paid"
    assert result.mode == "auto"


# --------------------------------------------------------------------------
# 3. Free-only mode: no paid key configured
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_free_only_mode_no_paid_key(mock_session, monkeypatch):
    """Without GOOGLE_API_KEY_PAID, selector uses free-only mode and skips DB."""
    monkeypatch.delenv("GOOGLE_API_KEY_PAID", raising=False)
    sel = UsageAwareKeySelector()

    with patch("src.services.key_selector.UsageRepository") as MockRepo:
        result = await sel.resolve(user_id=1, session=mock_session)
        MockRepo.assert_not_called()

    assert result.tier == "gemini_free"
    assert result.mode == "free_only"
    assert result.api_key == "test-free-key"


# --------------------------------------------------------------------------
# 4. Free-only mode: identical keys
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_free_only_mode_identical_keys(mock_session, monkeypatch):
    """When paid key == free key, selector enters free-only mode."""
    monkeypatch.setenv("GOOGLE_API_KEY_PAID", "test-free-key")
    sel = UsageAwareKeySelector()

    with patch("src.services.key_selector.UsageRepository") as MockRepo:
        result = await sel.resolve(user_id=1, session=mock_session)
        MockRepo.assert_not_called()

    assert result.tier == "gemini_free"
    assert result.mode == "free_only"


# --------------------------------------------------------------------------
# 5. Force tier env: free
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_force_tier_env_free(mock_session, monkeypatch):
    """GEMINI_FORCE_TIER=free forces free key, no DB call."""
    monkeypatch.setenv("GEMINI_FORCE_TIER", "free")
    sel = UsageAwareKeySelector()

    with patch("src.services.key_selector.UsageRepository") as MockRepo:
        result = await sel.resolve(user_id=1, session=mock_session)
        MockRepo.assert_not_called()

    assert result.tier == "gemini_free"
    assert result.mode == "forced_env"


# --------------------------------------------------------------------------
# 6. Force tier env: paid
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_force_tier_env_paid(mock_session, monkeypatch):
    """GEMINI_FORCE_TIER=paid forces paid key, no DB call."""
    monkeypatch.setenv("GEMINI_FORCE_TIER", "paid")
    sel = UsageAwareKeySelector()

    with patch("src.services.key_selector.UsageRepository") as MockRepo:
        result = await sel.resolve(user_id=1, session=mock_session)
        MockRepo.assert_not_called()

    assert result.tier == "gemini_paid"
    assert result.mode == "forced_env"


# --------------------------------------------------------------------------
# 7. Force tier request overrides env
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_force_tier_request_overrides_env(mock_session, monkeypatch):
    """force_tier param (priority 1) beats GEMINI_FORCE_TIER env (priority 2)."""
    monkeypatch.setenv("GEMINI_FORCE_TIER", "free")
    sel = UsageAwareKeySelector()

    with patch("src.services.key_selector.UsageRepository") as MockRepo:
        result = await sel.resolve(user_id=1, session=mock_session, force_tier="paid")
        MockRepo.assert_not_called()

    assert result.tier == "gemini_paid"
    assert result.mode == "forced_request"


# --------------------------------------------------------------------------
# 8. Force paid without paid key -> fallback to free
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_force_paid_without_paid_key(mock_session, monkeypatch):
    """Forcing paid tier in free-only mode falls back to free key."""
    monkeypatch.delenv("GOOGLE_API_KEY_PAID", raising=False)
    sel = UsageAwareKeySelector()

    result = await sel.resolve(user_id=1, session=mock_session, force_tier="paid")

    assert result.tier == "gemini_free"
    assert result.api_key == "test-free-key"


# --------------------------------------------------------------------------
# 9. Resolution tier values are valid
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolution_tier_values(selector, mock_session):
    """All resolution tiers are exactly 'gemini_free', 'gemini_paid', or 'exhausted'."""
    valid_tiers = {"gemini_free", "gemini_paid", "exhausted"}

    mock_check = AsyncMock(return_value=(True, {
        "used": 0, "limit": 15, "remaining": 15,
        "resets_at": "2026-03-25T00:00:00-07:00",
    }))
    with patch("src.services.key_selector.UsageRepository") as MockRepo:
        MockRepo.return_value.check_limit = mock_check
        result = await selector.resolve(user_id=1, session=mock_session)

    assert result.tier in valid_tiers


# --------------------------------------------------------------------------
# 10. Empty free key raises ValueError
# --------------------------------------------------------------------------

def test_empty_free_key_raises(monkeypatch):
    """Missing GOOGLE_API_KEY raises ValueError at construction."""
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GOOGLE_API_KEY"):
        UsageAwareKeySelector()


# --------------------------------------------------------------------------
# 11. Both tiers exhausted returns tier='exhausted'
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_returns_exhausted_both_tiers(selector, mock_session):
    """When both free and paid tiers are over limit, resolve returns exhausted."""
    mock_check = AsyncMock(side_effect=[
        (False, {"used": 15, "limit": 15, "remaining": 0,
                 "resets_at": "2026-03-25T00:00:00-07:00"}),
        (False, {"used": 100, "limit": 100, "remaining": 0,
                 "resets_at": "2026-03-25T00:00:00-07:00"}),
    ])
    with patch("src.services.key_selector.UsageRepository") as MockRepo:
        MockRepo.return_value.check_limit = mock_check
        result = await selector.resolve(user_id=1, session=mock_session)

    assert result.api_key == ""
    assert result.tier == "exhausted"
    assert result.mode == "auto"
    assert mock_check.await_count == 2


# --------------------------------------------------------------------------
# 12. Free-only mode exhausted returns tier='exhausted'
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_exhausted_free_only(mock_session, monkeypatch):
    """In free-only mode, when free tier is over limit, resolve returns exhausted."""
    monkeypatch.delenv("GOOGLE_API_KEY_PAID", raising=False)
    sel = UsageAwareKeySelector()

    mock_check = AsyncMock(return_value=(False, {
        "used": 15, "limit": 15, "remaining": 0,
        "resets_at": "2026-03-25T00:00:00-07:00",
    }))
    with patch("src.services.key_selector.UsageRepository") as MockRepo:
        MockRepo.return_value.check_limit = mock_check
        result = await sel.resolve(user_id=1, session=mock_session)

    assert result.tier == "exhausted"
    assert result.api_key == ""
    assert mock_check.await_count == 1


# --------------------------------------------------------------------------
# 13. Free exhausted but paid allowed returns paid key
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_paid_when_free_exhausted_paid_allowed(selector, mock_session):
    """When free is over limit but paid is allowed, resolve returns paid key."""
    mock_check = AsyncMock(side_effect=[
        (False, {"used": 15, "limit": 15, "remaining": 0,
                 "resets_at": "2026-03-25T00:00:00-07:00"}),
        (True, {"used": 50, "limit": 0, "remaining": -1,
                "resets_at": "2026-03-25T00:00:00-07:00"}),
    ])
    with patch("src.services.key_selector.UsageRepository") as MockRepo:
        MockRepo.return_value.check_limit = mock_check
        result = await selector.resolve(user_id=1, session=mock_session)

    assert result.api_key == "test-paid-key"
    assert result.tier == "gemini_paid"
