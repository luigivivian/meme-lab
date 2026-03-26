# Phase 7: Usage Tracking Table - Research

**Researched:** 2026-03-24
**Domain:** MySQL table design, Alembic migration, SQLAlchemy ORM, timezone-aware date bucketing
**Confidence:** HIGH

## Summary

Phase 7 adds a single `api_usage` table to MySQL via Alembic migration 008. The table tracks per-user per-day API consumption across all external services (gemini_image, gemini_text, gemini_web, comfyui) with timezone-correct daily reset at midnight Pacific Time. This phase is schema-only: no runtime logic, no repository, no endpoints.

The implementation is straightforward because the project already has 7 migrations, 13 ORM models, and well-established patterns for table creation, FK relationships, indexing, and TimestampMixin usage. The only nuance is the `date` column storing UTC DateTime (not a date type) with PT conversion deferred to the Python repository layer (Phase 8), and a UniqueConstraint on `(user_id, service, tier, date)` to enable Phase 8's atomic `INSERT ... ON DUPLICATE KEY UPDATE`.

**Primary recommendation:** Follow the exact patterns from migration 007 and the User model. The model is ~30 lines, the migration is ~40 lines, tests are ~60 lines. One plan with 2-3 tasks.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Track ALL external API services. Column `service` is `String(50)` with values: `gemini_image`, `gemini_text`, `gemini_web`, `comfyui`. Extensible without schema changes.
- **D-02:** Tier values are simple `free`/`paid` -- matches existing `User.active_key_tier` values.
- **D-03:** The `date` column stores UTC `DateTime`, NOT a PT date. All reads convert UTC to America/Los_Angeles before bucketing by day.
- **D-04:** PT conversion lives in the Python repository layer (using `zoneinfo`), not MySQL `CONVERT_TZ()`. Preserves SQLite compatibility for tests.
- **D-05:** `status` column represents call outcome with values: `success`, `error`, `rejected`.
- **D-06:** Only `success` rows count toward the daily limit. Failed API calls (`error`) do NOT consume quota.
- **D-07:** `user_id` is a nullable FK to `users.id`. `NULL` = system/shared key usage.
- **D-08:** UniqueConstraint on `(user_id, service, tier, date)` -- one row per user/service/tier/day. Phase 8 will use `INSERT ... ON DUPLICATE KEY UPDATE usage_count = usage_count + 1`.

### Claude's Discretion
- Migration file naming and revision chain (should be 008 after 007)
- Additional indexes beyond the unique constraint (e.g., idx_api_usage_user_id, idx_api_usage_date)
- Whether to add a `usage_count` default of 0 or 1 on first insert
- ORM relationship back-populates on User model

### Deferred Ideas (OUT OF SCOPE)
- UsageRepository with atomic increment -- Phase 8
- Usage read endpoint (GET /auth/me/usage) -- Phase 8 (QUOT-03)
- UsageAwareKeySelector -- Phase 9 (QUOT-04, QUOT-05)
- Per-endpoint HTTP rate limiting -- Out of scope per REQUIREMENTS.md
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QUOT-01 | Tabela api_usage no MySQL (user_id, service, tier, date, count, status) | Model definition follows User/RefreshToken pattern; migration 008 chains from 007; all column types verified against decisions D-01 through D-08 |
| QUOT-07 | Reset diario do contador (timezone-aware) | `date` column stores UTC DateTime (D-03); PT conversion via `zoneinfo.ZoneInfo('America/Los_Angeles')` in repository layer (D-04); Python 3.14 has zoneinfo built-in (verified); SQLite test compatibility preserved by keeping conversion in Python |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.47 | ORM model definition | Already in project, all 13 models use it |
| Alembic | 1.18.4 | Migration 008 | Already configured, 7 migrations exist |
| zoneinfo | stdlib | PT timezone conversion | Built into Python 3.9+, project uses 3.14 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.0.2 | Test model and migration | Schema validation tests |

No new packages needed. Everything is already installed.

## Architecture Patterns

### Model Definition Pattern (from models.py)
```python
# Section comment block
# ============================================================
# 14. api_usage
# ============================================================

class ApiUsage(TimestampMixin, Base):
    __tablename__ = "api_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    service: Mapped[str] = mapped_column(String(50), nullable=False)
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")
    status: Mapped[str] = mapped_column(String(20), nullable=False)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="api_usage_records")

    __table_args__ = (
        UniqueConstraint("user_id", "service", "tier", "date", name="uq_api_usage_user_service_tier_date"),
        Index("idx_api_usage_user_id", "user_id"),
        Index("idx_api_usage_date", "date"),
        Index("idx_api_usage_service", "service"),
    )
```

### Migration Pattern (from 007_add_refresh_tokens.py)
```python
revision: str = '008'
down_revision: Union[str, None] = '007'

def upgrade() -> None:
    op.create_table(
        "api_usage",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("service", sa.String(50), nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("date", sa.DateTime(), nullable=False),
        sa.Column("usage_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "service", "tier", "date", name="uq_api_usage_user_service_tier_date"),
    )
    op.create_index("idx_api_usage_user_id", "api_usage", ["user_id"])
    op.create_index("idx_api_usage_date", "api_usage", ["date"])
    op.create_index("idx_api_usage_service", "api_usage", ["service"])

def downgrade() -> None:
    op.drop_index("idx_api_usage_service", table_name="api_usage")
    op.drop_index("idx_api_usage_date", table_name="api_usage")
    op.drop_index("idx_api_usage_user_id", table_name="api_usage")
    op.drop_table("api_usage")
```

### Test Pattern (from test_users_table.py)
```python
def test_api_usage_model_exists():
    from src.database.models import ApiUsage
    assert ApiUsage.__tablename__ == "api_usage"

def test_api_usage_columns():
    from src.database.models import ApiUsage
    table = ApiUsage.__table__
    cols = {c.name: c for c in table.columns}
    # Check each column type, nullability, defaults
    assert "user_id" in cols
    assert cols["user_id"].nullable is True
    # ... etc

def test_api_usage_unique_constraint():
    from src.database.models import ApiUsage
    table = ApiUsage.__table__
    uqs = [c for c in table.constraints if isinstance(c, UniqueConstraint)]
    # Verify the composite unique constraint exists
```

### Anti-Patterns to Avoid
- **Date column as `Date` type:** Decision D-03 explicitly requires `DateTime` (UTC timestamp), not `Date`. The PT bucketing happens in Python, not at the schema level.
- **Non-nullable user_id:** Decision D-07 requires nullable FK for system/shared key usage.
- **MySQL-specific features in model:** No `CONVERT_TZ()`, no MySQL-only defaults. Must work with SQLite for tests (D-04).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Timezone conversion | Custom UTC offset math | `zoneinfo.ZoneInfo('America/Los_Angeles')` | Handles DST transitions correctly |
| Atomic counter | Custom locking logic | Phase 8's `INSERT ... ON DUPLICATE KEY UPDATE` | UniqueConstraint enables this pattern |
| Timestamp columns | Manual created_at/updated_at | `TimestampMixin` from `base.py` | Already standardized across 13 models |

## Common Pitfalls

### Pitfall 1: UniqueConstraint with nullable user_id
**What goes wrong:** In SQL standard, `NULL != NULL`, so multiple rows with `user_id=NULL` and same service/tier/date would NOT violate the unique constraint. This means system-level (shared key) usage could have duplicate rows.
**Why it happens:** MySQL follows SQL standard for NULL in unique constraints.
**How to avoid:** This is actually acceptable for Phase 7 (table only). Phase 8 must handle the NULL case in its repository logic -- either by using a sentinel value (e.g., user_id=0) or by adding application-level dedup. Document this for Phase 8 planner.
**Warning signs:** Multiple rows with user_id=NULL for same service/tier/date.

### Pitfall 2: Migration revision chain conflict
**What goes wrong:** If there's an uncommitted migration or the chain breaks, `alembic upgrade head` fails.
**Why it happens:** There's a stray `ee583b64523f_add_rendering_column_to_characters.py` in the migrations directory that could conflict.
**How to avoid:** Verify the current head with `alembic heads` before creating 008. The chain should be 007 -> 008 cleanly. The stray migration may be on a different branch.
**Warning signs:** `alembic upgrade head` shows "Multiple heads" error.

### Pitfall 3: ondelete behavior for nullable FK
**What goes wrong:** Using `CASCADE` on a nullable FK deletes usage records when user is deleted, losing historical data.
**Why it happens:** Default FK behavior varies.
**How to avoid:** Use `ondelete="SET NULL"` so usage records persist even after user deletion. The user_id becomes NULL (same as system usage). This preserves audit trail.

### Pitfall 4: server_default for usage_count
**What goes wrong:** If `server_default` is missing, MySQL inserts may fail when Phase 8 does `INSERT ... ON DUPLICATE KEY UPDATE`.
**Why it happens:** MySQL needs a default or explicit value for non-nullable columns.
**How to avoid:** Set `server_default="1"` on `usage_count`. First insert = 1 (first API call), subsequent increments via `ON DUPLICATE KEY UPDATE usage_count = usage_count + 1`.

## Code Examples

### Model file location and imports
```python
# In src/database/models.py, add after RefreshToken (section 14)
# Imports already present: DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
# Need to verify: Optional is already imported from typing
```

### User model back-populate addition
```python
# Add to User class in models.py (after characters relationship):
api_usage_records: Mapped[list["ApiUsage"]] = relationship(back_populates="user")
```

### Timezone conversion (Phase 8 reference, not Phase 7 code)
```python
# This is how Phase 8 will use the date column -- included for planner context
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

PT = ZoneInfo("America/Los_Angeles")

def get_pt_date_bucket(utc_dt: datetime) -> datetime:
    """Convert UTC datetime to PT date bucket (midnight PT of that day)."""
    pt_dt = utc_dt.replace(tzinfo=timezone.utc).astimezone(PT)
    return pt_dt.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
```

## Decisions for Claude's Discretion

### Migration naming
**Recommendation:** `008_add_api_usage_table.py` with `revision = '008'` and `down_revision = '007'`. Follows exact naming pattern of 006 and 007.

### Additional indexes
**Recommendation:** Add three indexes beyond the UniqueConstraint:
1. `idx_api_usage_user_id` -- fast lookups per user (Phase 8 queries)
2. `idx_api_usage_date` -- date range queries (Phase 11 dashboard)
3. `idx_api_usage_service` -- per-service filtering

These are cheap to add now and prevent ALTER TABLE later.

### usage_count default
**Recommendation:** `server_default="1"`, ORM `default=1`. First insert represents the first API call. Phase 8 increments from there. This avoids the awkward "insert with 0 then immediately update to 1" pattern.

### ORM relationship
**Recommendation:** Add `api_usage_records` relationship on User with `back_populates="user"`. Lightweight, no schema impact, enables eager loading in Phase 11.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | pyproject.toml |
| Quick run command | `python -m pytest tests/test_api_usage.py -x -v` |
| Full suite command | `python -m pytest tests/ -x -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUOT-01 | ApiUsage model has correct columns (user_id, service, tier, date, usage_count, status) | unit | `python -m pytest tests/test_api_usage.py::test_api_usage_columns -x` | No -- Wave 0 |
| QUOT-01 | UniqueConstraint on (user_id, service, tier, date) exists | unit | `python -m pytest tests/test_api_usage.py::test_api_usage_unique_constraint -x` | No -- Wave 0 |
| QUOT-01 | user_id FK references users.id, nullable | unit | `python -m pytest tests/test_api_usage.py::test_api_usage_user_fk -x` | No -- Wave 0 |
| QUOT-01 | Migration 008 upgrade creates table | unit | `python -m pytest tests/test_api_usage.py::test_migration_008_exists -x` | No -- Wave 0 |
| QUOT-07 | date column is DateTime (UTC storage) | unit | `python -m pytest tests/test_api_usage.py::test_date_column_is_datetime -x` | No -- Wave 0 |
| QUOT-01 | User model has api_usage_records relationship | unit | `python -m pytest tests/test_api_usage.py::test_user_api_usage_relationship -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_api_usage.py -x -v`
- **Per wave merge:** `python -m pytest tests/ -x -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_api_usage.py` -- covers QUOT-01, QUOT-07 (model columns, constraints, FK, migration)

## Sources

### Primary (HIGH confidence)
- `src/database/models.py` lines 506-547 -- User and RefreshToken model patterns
- `src/database/base.py` -- TimestampMixin and Base classes
- `src/database/migrations/versions/007_add_refresh_tokens.py` -- Latest migration pattern
- `src/database/migrations/versions/006_add_users_table.py` -- Table + FK migration pattern
- `tests/test_users_table.py` -- Test pattern for model validation
- `src/database/repositories/schedule_repo.py` -- Repository pattern reference

### Secondary (MEDIUM confidence)
- SQLAlchemy 2.0 UniqueConstraint with nullable columns behavior -- standard SQL NULL != NULL semantics

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in project, versions verified via imports
- Architecture: HIGH -- exact patterns exist in 007 migration and User model, copy-and-adapt
- Pitfalls: HIGH -- nullable unique constraint and ondelete behavior are well-documented SQL semantics

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable -- schema design, no fast-moving dependencies)
