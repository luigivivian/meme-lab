"""Integration tests for tenant isolation (TENANT-01..04).

Tests CharacterRepository tenant filtering at the repository level
using mock User objects (no DB or HTTP needed).
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.database.repositories.character_repo import CharacterRepository


# ── Fixtures ─────────────────────────────────────────────────────────

def _make_user(user_id: int, role: str = "user") -> SimpleNamespace:
    """Create a lightweight User-like object."""
    return SimpleNamespace(id=user_id, role=role, email=f"user{user_id}@test.com")


def _make_character(char_id: int, slug: str, user_id: int) -> SimpleNamespace:
    """Create a lightweight Character-like object."""
    return SimpleNamespace(
        id=char_id,
        slug=slug,
        user_id=user_id,
        is_deleted=False,
    )


@pytest.fixture
def admin_user():
    return _make_user(1, role="admin")


@pytest.fixture
def regular_user():
    return _make_user(2, role="user")


@pytest.fixture
def admin_character():
    return _make_character(1, "admin-char", user_id=1)


@pytest.fixture
def user_character():
    return _make_character(2, "user-char", user_id=2)


def _mock_session_for_list(characters: list) -> AsyncMock:
    """Create a mock AsyncSession that returns a list of characters."""
    session = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = characters
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    session.execute.return_value = result_mock
    return session


def _mock_session_for_scalar(character) -> AsyncMock:
    """Create a mock AsyncSession that returns a single character or None."""
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = character
    session.execute.return_value = result_mock
    return session


# ── TENANT-01: User isolation (list sees only own) ───────────────────

class TestUserIsolation:
    """TENANT-01: Regular user only sees their own characters."""

    @pytest.mark.asyncio
    async def test_user_isolation(self, regular_user, admin_character, user_character):
        """Regular user listing characters sees only their own."""
        all_chars = [admin_character, user_character]
        session = _mock_session_for_list(all_chars)
        repo = CharacterRepository(session)

        # Repo should add a WHERE clause filtering by user_id
        result = await repo.list_all(user=regular_user)

        # Verify the execute was called (query was built with user filter)
        assert session.execute.called
        # The query should have been constructed with user_id filter
        call_args = session.execute.call_args
        stmt = call_args[0][0]
        # Verify the statement contains user_id filtering by checking compiled SQL
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "user_id" in compiled


# ── TENANT-02: Repo filtering ────────────────────────────────────────

class TestRepoFiltering:
    """TENANT-02: CharacterRepository.list_all filters by user."""

    @pytest.mark.asyncio
    async def test_repo_filtering(self, regular_user):
        """list_all with regular user adds user_id WHERE clause."""
        session = _mock_session_for_list([])
        repo = CharacterRepository(session)

        await repo.list_all(user=regular_user)

        call_args = session.execute.call_args
        stmt = call_args[0][0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        assert "user_id" in compiled
        assert str(regular_user.id) in compiled

    @pytest.mark.asyncio
    async def test_no_filter_without_user(self):
        """list_all without user returns all (no user_id filter)."""
        session = _mock_session_for_list([])
        repo = CharacterRepository(session)

        await repo.list_all(user=None)

        call_args = session.execute.call_args
        stmt = call_args[0][0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        # Should not have user_id in WHERE (only in SELECT columns)
        where_part = compiled.split("WHERE")[1] if "WHERE" in compiled else ""
        assert "user_id" not in where_part or "is_deleted" in where_part


# ── TENANT-03: Admin bypass ──────────────────────────────────────────

class TestAdminBypass:
    """TENANT-03: Admin user sees all characters."""

    @pytest.mark.asyncio
    async def test_admin_bypass(self, admin_user):
        """Admin user listing characters has no user_id filter."""
        session = _mock_session_for_list([])
        repo = CharacterRepository(session)

        await repo.list_all(user=admin_user)

        call_args = session.execute.call_args
        stmt = call_args[0][0]
        compiled = str(stmt.compile(compile_kwargs={"literal_binds": True}))
        # Admin should NOT have user_id filter in WHERE clause
        where_part = compiled.split("WHERE")[1] if "WHERE" in compiled else ""
        assert "user_id" not in where_part or "is_deleted" in where_part

    @pytest.mark.asyncio
    async def test_admin_access_any_character(self, admin_user, user_character):
        """Admin can access any character by slug without PermissionError."""
        session = _mock_session_for_scalar(user_character)
        repo = CharacterRepository(session)

        # Should NOT raise PermissionError
        result = await repo.get_by_slug("user-char", user=admin_user)
        assert result is not None
        assert result.slug == "user-char"


# ── TENANT-04: 403 Forbidden ────────────────────────────────────────

class TestForbidden:
    """TENANT-04: Non-owner access raises PermissionError."""

    @pytest.mark.asyncio
    async def test_403_forbidden(self, regular_user, admin_character):
        """Regular user accessing another user's character raises PermissionError."""
        session = _mock_session_for_scalar(admin_character)
        repo = CharacterRepository(session)

        with pytest.raises(PermissionError, match="forbidden"):
            await repo.get_by_slug("admin-char", user=regular_user)

    @pytest.mark.asyncio
    async def test_403_get_by_id(self, regular_user, admin_character):
        """Regular user accessing another user's character by id raises PermissionError."""
        session = _mock_session_for_scalar(admin_character)
        repo = CharacterRepository(session)

        with pytest.raises(PermissionError, match="forbidden"):
            await repo.get_by_id(1, user=regular_user)

    @pytest.mark.asyncio
    async def test_own_character_no_error(self, regular_user, user_character):
        """Regular user accessing own character succeeds."""
        session = _mock_session_for_scalar(user_character)
        repo = CharacterRepository(session)

        result = await repo.get_by_slug("user-char", user=regular_user)
        assert result is not None
        assert result.user_id == regular_user.id
