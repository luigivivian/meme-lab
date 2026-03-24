"""Tests for AUTH-07: User model, Character FK, and relationships."""

import pytest
from sqlalchemy import inspect as sa_inspect


def test_user_model_exists():
    """User class is importable and has correct tablename."""
    from src.database.models import User

    assert hasattr(User, "__tablename__")
    assert User.__tablename__ == "users"


def test_users_columns():
    """User model has all required columns with correct types and defaults."""
    from src.database.models import User

    table = User.__table__
    cols = {c.name: c for c in table.columns}

    # id — Integer PK
    assert "id" in cols
    assert cols["id"].primary_key is True

    # email — String(255), unique, not nullable
    assert "email" in cols
    assert cols["email"].nullable is False
    assert cols["email"].unique is True
    assert cols["email"].type.length == 255

    # hashed_password — String(200), not nullable
    assert "hashed_password" in cols
    assert cols["hashed_password"].nullable is False
    assert cols["hashed_password"].type.length == 200

    # role — String(20), default "user"
    assert "role" in cols
    assert cols["role"].type.length == 20
    assert cols["role"].server_default is not None

    # is_active — Boolean, default True
    assert "is_active" in cols
    assert cols["is_active"].server_default is not None

    # display_name — String(200), nullable
    assert "display_name" in cols
    assert cols["display_name"].nullable is True
    assert cols["display_name"].type.length == 200

    # gemini_free_key — Text, nullable
    assert "gemini_free_key" in cols
    assert cols["gemini_free_key"].nullable is True

    # gemini_paid_key — Text, nullable
    assert "gemini_paid_key" in cols
    assert cols["gemini_paid_key"].nullable is True

    # active_key_tier — String(20), default "free"
    assert "active_key_tier" in cols
    assert cols["active_key_tier"].type.length == 20
    assert cols["active_key_tier"].server_default is not None

    # Timestamps from TimestampMixin
    assert "created_at" in cols
    assert "updated_at" in cols


def test_character_user_id_column():
    """Character model has user_id column (Integer, nullable, FK to users.id)."""
    from src.database.models import Character

    table = Character.__table__
    cols = {c.name: c for c in table.columns}

    assert "user_id" in cols
    assert cols["user_id"].nullable is True

    # Check FK
    fks = [fk.target_fullname for fk in cols["user_id"].foreign_keys]
    assert "users.id" in fks


def test_character_owner_relationship():
    """Character model has 'owner' relationship attribute."""
    from src.database.models import Character

    mapper = sa_inspect(Character)
    rel_names = [r.key for r in mapper.relationships]
    assert "owner" in rel_names


def test_user_characters_relationship():
    """User model has 'characters' relationship attribute."""
    from src.database.models import User

    mapper = sa_inspect(User)
    rel_names = [r.key for r in mapper.relationships]
    assert "characters" in rel_names
