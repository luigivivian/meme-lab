"""Tests for QUOT-01 and QUOT-07: ApiUsage model schema validation."""
import pytest
from sqlalchemy import UniqueConstraint, inspect as sa_inspect, DateTime


def test_api_usage_model_exists():
    from src.database.models import ApiUsage
    assert hasattr(ApiUsage, "__tablename__")
    assert ApiUsage.__tablename__ == "api_usage"


def test_api_usage_columns():
    from src.database.models import ApiUsage
    table = ApiUsage.__table__
    cols = {c.name: c for c in table.columns}
    # id — Integer PK
    assert "id" in cols
    assert cols["id"].primary_key is True
    # user_id — Integer, nullable (D-07: NULL = system/shared key)
    assert "user_id" in cols
    assert cols["user_id"].nullable is True
    # service — String(50), not nullable (D-01)
    assert "service" in cols
    assert cols["service"].nullable is False
    assert cols["service"].type.length == 50
    # tier — String(20), not nullable (D-02)
    assert "tier" in cols
    assert cols["tier"].nullable is False
    assert cols["tier"].type.length == 20
    # date — DateTime, not nullable (D-03: stores UTC)
    assert "date" in cols
    assert cols["date"].nullable is False
    # usage_count — Integer, not nullable, server_default "1"
    assert "usage_count" in cols
    assert cols["usage_count"].nullable is False
    assert cols["usage_count"].server_default is not None
    # status — String(20), not nullable (D-05)
    assert "status" in cols
    assert cols["status"].nullable is False
    assert cols["status"].type.length == 20
    # TimestampMixin columns
    assert "created_at" in cols
    assert "updated_at" in cols


def test_api_usage_user_fk():
    from src.database.models import ApiUsage
    table = ApiUsage.__table__
    cols = {c.name: c for c in table.columns}
    fks = list(cols["user_id"].foreign_keys)
    assert len(fks) == 1
    assert str(fks[0].target_fullname) == "users.id"


def test_api_usage_unique_constraint():
    from src.database.models import ApiUsage
    table = ApiUsage.__table__
    uqs = [c for c in table.constraints if isinstance(c, UniqueConstraint)]
    uq_names = [uq.name for uq in uqs]
    assert "uq_api_usage_user_service_tier_date" in uq_names


def test_api_usage_indexes():
    from src.database.models import ApiUsage
    table = ApiUsage.__table__
    idx_names = [idx.name for idx in table.indexes]
    assert "idx_api_usage_user_id" in idx_names
    assert "idx_api_usage_date" in idx_names
    assert "idx_api_usage_service" in idx_names


def test_date_column_is_datetime():
    """QUOT-07: date column must be DateTime (UTC storage), not Date."""
    from src.database.models import ApiUsage
    table = ApiUsage.__table__
    cols = {c.name: c for c in table.columns}
    assert isinstance(cols["date"].type, DateTime)


def test_user_api_usage_relationship():
    from src.database.models import User
    assert hasattr(User, "api_usage_records")
