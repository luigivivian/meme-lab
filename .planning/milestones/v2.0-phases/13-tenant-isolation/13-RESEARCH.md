# Phase 13: Tenant Isolation - Research

**Researched:** 2026-03-24
**Domain:** Multi-tenant data isolation in FastAPI + SQLAlchemy async
**Confidence:** HIGH

## Summary

Phase 13 adds row-level tenant isolation to an existing FastAPI + SQLAlchemy 2.0 async application. All routes already inject `get_current_user` (returning a User ORM object with id, email, role), but no repository method currently filters by user ownership. The core work is: (1) modify all repository query methods to accept and filter by `user_id`, (2) implement admin bypass when `user.role == "admin"`, (3) create an Alembic migration to backfill existing data to the seed admin user and enforce NOT NULL constraints, and (4) add a Theme.user_id column for user-created themes.

The ownership model is transitive: User owns Characters, and Characters own everything else (PipelineRun, ContentPackage, GeneratedImage, BatchJob, ScheduledPost, WorkOrder). This means child table queries join through character_id to verify ownership rather than adding user_id columns to every table. This is a clean, normalized approach that avoids data duplication.

**Primary recommendation:** Implement isolation at the repository layer only. Each repo method receives a `User` object (not just user_id) so it can check `user.role == "admin"` for bypass. Create a helper dependency `get_user_character(slug, user, session)` that validates character ownership in one call, reusable across all character-scoped routes.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Transitive ownership via character -- PipelineRun, ContentPackage, GeneratedImage, BatchJob, ScheduledPost, WorkOrder are owned by character, which has user_id. Repos join through character to filter by user. No new user_id columns needed on child tables.
- **D-02:** PipelineRun.character_id becomes required (non-nullable). Every run must belong to a character. Orphan runs are not allowed.
- **D-03:** Theme ownership is global + user themes. Global themes (no user_id) visible to all. Users can create their own themes via a new user_id column on Theme. Repos return global + user's own themes. Admin can manage global themes.
- **D-04:** 403 for accessing another user's data, 404 for truly non-existent resources. Standard REST semantics -- reveals existence but enforces isolation.
- **D-05:** Enforcement at repository level. All repo methods take user_id parameter and filter by it. Routes pass current_user.id to repos. Repos are the single enforcement point.
- **D-06:** All routes require authentication. Every route except /auth/*, /health, and /docs injects get_current_user. This activates the deferred AUTH-05 from Phase 4. Unauthenticated requests get 401.
- **D-07:** Admin bypass via role check in repos. If user.role == "admin", repos skip user_id filtering and return all data. No extra headers, query params, or separate endpoints needed. Admin always sees everything.
- **D-08:** Assign all existing data to seed admin (user id=1). Migration backfills all characters with null user_id to admin. PipelineRuns with null character_id get assigned to default character (mago-mestre).
- **D-09:** Character.user_id becomes NOT NULL after backfill. Enforces ownership at DB level -- impossible to create orphan characters.
- **D-10:** PipelineRun.character_id becomes NOT NULL after backfill. Consistent with D-02 -- every run belongs to a character, which belongs to a user.

### Claude's Discretion
- Which repos need a dedicated `user_id` parameter vs which can derive ownership through joins
- Whether to add a helper dependency like `get_user_character()` that validates character ownership in one call
- Exact migration ordering and Alembic revision chaining
- How AgentStat and TrendEvent are handled (monitoring data, may remain global or scoped to pipeline run)
- Implementation of the 403 check -- whether to fetch-then-check or use query filtering

### Deferred Ideas (OUT OF SCOPE)
- Admin bypass mechanism -- User chose the simplest approach (role check in repos). If more granular admin access needed later (e.g., "view as user X"), can add X-Admin-As-User header in a future phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TENANT-01 | User sees only their own data across all resources (characters, runs, images, posts) | Repository-level filtering with user_id parameter; transitive ownership via Character; helper dependency `get_user_character()` |
| TENANT-02 | All tables have user_id FK with scoped queries (pipeline_runs, content_packages, generated_images, scheduled_posts, work_orders, batch_jobs, themes) | Transitive ownership through character_id join (no new columns on child tables except Theme.user_id); all repo methods updated |
| TENANT-03 | Admin user can access all users' data via admin bypass | `user.role == "admin"` check in repos skips user_id filtering; User model already has role field |
| TENANT-04 | Cross-user data access returns 403 (not 404) | Fetch-then-check pattern: query without user filter, then compare ownership, raise 403 if mismatch |
</phase_requirements>

## Architecture Patterns

### Recommended Project Structure (changes only)

```
src/
  api/
    deps.py                    # Add get_user_character() helper dependency
    routes/
      *.py                     # All routes already have get_current_user; update repo calls
  database/
    repositories/
      character_repo.py        # Add user_id filtering to all methods
      pipeline_repo.py         # Add character ownership join for user filtering
      content_repo.py          # Add character ownership join for user filtering
      job_repo.py              # Add character ownership join for user filtering
      theme_repo.py            # Add user_id filtering (global + user themes)
      schedule_repo.py         # Add character ownership join for user filtering
      usage_repo.py            # Already user-scoped -- no changes needed
    migrations/versions/
      010_tenant_isolation.py   # Backfill + NOT NULL constraints + Theme.user_id
    models.py                   # Theme.user_id column, PipelineRun.character_id NOT NULL
```

### Pattern 1: Repository-Level Tenant Filtering

**What:** Every repository query method receives a `User` object. If `user.role != "admin"`, queries are filtered by ownership. Admin users see all data.

**When to use:** Every read/list/get operation across all repositories.

**Example (CharacterRepository):**
```python
from src.database.models import Character, User

class CharacterRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_all(
        self,
        user: User | None = None,
        include_deleted: bool = False,
    ) -> list[Character]:
        stmt = select(Character).order_by(Character.created_at.desc())
        if not include_deleted:
            stmt = stmt.where(Character.is_deleted == False)
        # Tenant filtering: admin sees all, user sees own
        if user and user.role != "admin":
            stmt = stmt.where(Character.user_id == user.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_slug(
        self,
        slug: str,
        user: User | None = None,
        include_deleted: bool = False,
    ) -> Character | None:
        stmt = select(Character).where(Character.slug == slug)
        if not include_deleted:
            stmt = stmt.where(Character.is_deleted == False)
        result = await self.session.execute(stmt)
        character = result.scalar_one_or_none()
        if not character:
            return None  # Caller raises 404
        # Ownership check for non-admin
        if user and user.role != "admin" and character.user_id != user.id:
            raise PermissionError("forbidden")  # Route catches -> 403
        return character
```

### Pattern 2: Transitive Ownership Join (Child Tables)

**What:** For tables owned by Character (PipelineRun, ContentPackage, etc.), filter by joining to Character.user_id rather than adding user_id to every table.

**Example (PipelineRunRepository):**
```python
async def list_runs(
    self,
    user: User | None = None,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
    character_id: int | None = None,
) -> list[PipelineRun]:
    stmt = select(PipelineRun).order_by(PipelineRun.started_at.desc())
    if status:
        stmt = stmt.where(PipelineRun.status == status)
    if character_id is not None:
        stmt = stmt.where(PipelineRun.character_id == character_id)
    # Tenant filter via character join
    if user and user.role != "admin":
        stmt = stmt.join(Character, PipelineRun.character_id == Character.id)
        stmt = stmt.where(Character.user_id == user.id)
    stmt = stmt.offset(offset).limit(limit)
    result = await self.session.execute(stmt)
    return list(result.scalars().all())
```

### Pattern 3: Helper Dependency for Character Ownership

**What:** A reusable FastAPI dependency that loads a character by slug and validates the current user owns it. Used by all character-scoped routes.

**Example (deps.py):**
```python
async def get_user_character(
    slug: str,
    current_user: User,
    session: AsyncSession,
) -> Character:
    """Load character by slug, enforce ownership. Raises 404 or 403."""
    from src.database.repositories.character_repo import CharacterRepository
    repo = CharacterRepository(session)
    character = await repo.get_by_slug(slug)
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    if current_user.role != "admin" and character.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return character
```

### Pattern 4: 403 vs 404 Implementation (D-04)

**What:** Fetch-then-check pattern. Query the resource without user filter, then compare ownership. This distinguishes "doesn't exist" (404) from "belongs to someone else" (403).

**Why fetch-then-check vs query filtering:** Query filtering (adding WHERE user_id = X) would always return None for both cases, making it impossible to return 403. The decision D-04 requires 403 for cross-user access, so we must fetch first, then check.

**Example:**
```python
async def get_by_id(self, resource_id: int, user: User | None = None):
    stmt = select(Resource).where(Resource.id == resource_id)
    result = await self.session.execute(stmt)
    resource = result.scalar_one_or_none()
    if not resource:
        return None  # Caller raises 404
    if user and user.role != "admin":
        # For child tables, check via character
        character = await self.session.get(Character, resource.character_id)
        if character and character.user_id != user.id:
            raise PermissionError("forbidden")
    return resource
```

**Important:** For list operations, query filtering IS appropriate (just show the user's own data). The fetch-then-check pattern is for single-resource lookups (get_by_id, get_by_slug, etc.).

### Anti-Patterns to Avoid

- **Adding user_id to every table:** Violates D-01. Child tables derive ownership through character_id. Adding redundant user_id columns creates sync problems.
- **Filtering in routes instead of repos:** Violates D-05. Routes should only pass the user; repos enforce the filter. This keeps the enforcement point single and auditable.
- **Using 404 for forbidden resources:** Violates D-04. The decision explicitly requires 403 for cross-user access so the user knows the resource exists but they lack permission.
- **Skipping admin bypass for specific routes:** D-07 says admin always sees everything. No exceptions unless explicitly changed.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Permission error propagation | Custom exception middleware | Python `PermissionError` caught in route with `try/except` -> 403 | Simple, no middleware needed |
| Character ownership validation | Inline checks in every route | `get_user_character()` helper in deps.py | DRY, 20+ routes need this |
| Migration data backfill | Manual SQL scripts | Alembic `op.execute()` with UPDATE statements | Versioned, reversible, standard |

**Key insight:** The codebase already has all infrastructure needed (get_current_user, User.role, Character.user_id FK). This phase is purely about wiring the existing auth into the repo layer and adding the ownership filter.

## Common Pitfalls

### Pitfall 1: N+1 Queries in Transitive Ownership Checks

**What goes wrong:** For child table single-resource lookups, loading the Character to check user_id creates an extra query per access.
**Why it happens:** The fetch-then-check pattern for 403 requires loading the parent Character.
**How to avoid:** For list operations, use JOIN to filter. For single lookups, the extra query is acceptable (one additional SELECT by PK). Do NOT eagerly load character relationships on every query.
**Warning signs:** Multiple queries per request visible in SQL logging.

### Pitfall 2: Breaking the Pipeline Background Task

**What goes wrong:** The pipeline runs in a background task (`_run_pipeline_task`) that creates its own session. If repos now require a user parameter, the background task has no user context.
**Why it happens:** Background tasks don't have a request context with auth headers.
**How to avoid:** The pipeline background task already has `character_id`. Since it's an internal operation (not user-facing), pass `user=None` to repo methods. When user is None, repos skip tenant filtering (internal/system operation). Alternatively, pass the user object captured at request time into the background task.
**Warning signs:** Pipeline runs failing with missing user parameter errors.

### Pitfall 3: Migration Order Matters

**What goes wrong:** Trying to ALTER COLUMN to NOT NULL before backfilling data causes constraint violations.
**Why it happens:** Existing rows have NULL character_id or user_id.
**How to avoid:** Migration must: (1) Ensure admin user exists (id=1), (2) Ensure default character exists, (3) UPDATE characters SET user_id=1 WHERE user_id IS NULL, (4) UPDATE pipeline_runs SET character_id=(default char id) WHERE character_id IS NULL, (5) ALTER character.user_id to NOT NULL, (6) ALTER pipeline_runs.character_id to NOT NULL, (7) ADD Theme.user_id column (nullable).
**Warning signs:** Alembic upgrade failing with "Column cannot be null" errors.

### Pitfall 4: Theme Dual Ownership Model

**What goes wrong:** Themes have three ownership modes: global (no user_id, no character_id), user-owned (user_id set, no character_id), and character-scoped (character_id set). Queries must handle all three.
**Why it happens:** D-03 adds user themes alongside existing global and character themes.
**How to avoid:** ThemeRepository.list_effective() must return: (1) global themes (user_id IS NULL AND character_id IS NULL), (2) user's own themes (user_id = current_user.id), (3) character-specific themes if character_id provided. Admin sees all.
**Warning signs:** Users seeing other users' custom themes, or global themes disappearing.

### Pitfall 5: AgentStat and TrendEvent Are Pipeline-Internal

**What goes wrong:** Trying to add tenant filtering to AgentStat/TrendEvent when they're monitoring data scoped to pipeline runs.
**Why it happens:** Over-applying tenant isolation to data that's already transitively scoped.
**How to avoid:** AgentStat and TrendEvent are children of PipelineRun. If you filter PipelineRun by user, the child data is automatically scoped. No direct user filtering needed on these tables -- they're only accessed via pipeline_run_id which is already tenant-filtered.
**Warning signs:** Unnecessary joins or redundant filtering on monitoring tables.

### Pitfall 6: PermissionError vs HTTPException in Repos

**What goes wrong:** Repos raising HTTPException (a FastAPI concept) breaks separation of concerns.
**Why it happens:** It's tempting to raise HTTPException directly in repos.
**How to avoid:** Repos should raise `PermissionError("forbidden")` (a plain Python exception). Routes catch `PermissionError` and convert to `HTTPException(403)`. This keeps repos framework-agnostic.
**Warning signs:** Repos importing FastAPI modules.

## Code Examples

### Migration 010: Tenant Isolation Backfill

```python
"""tenant isolation: backfill ownership, enforce NOT NULL, add Theme.user_id

Revision ID: 010
Revises: 009
"""
from alembic import op
import sqlalchemy as sa

revision = '010'
down_revision = '009'

def upgrade() -> None:
    # 1. Backfill characters.user_id to admin (id=1)
    op.execute("UPDATE characters SET user_id = 1 WHERE user_id IS NULL")

    # 2. Find default character for orphan pipeline runs
    # Use subquery to get mago-mestre id, fallback to id=1
    op.execute("""
        UPDATE pipeline_runs SET character_id = (
            SELECT id FROM characters WHERE slug = 'mago-mestre' LIMIT 1
        ) WHERE character_id IS NULL
    """)

    # 3. Enforce NOT NULL on characters.user_id
    # MySQL: ALTER COLUMN syntax
    op.alter_column('characters', 'user_id',
                    existing_type=sa.Integer(),
                    nullable=False)

    # 4. Enforce NOT NULL on pipeline_runs.character_id
    op.alter_column('pipeline_runs', 'character_id',
                    existing_type=sa.Integer(),
                    nullable=False)

    # 5. Add user_id to themes (nullable -- global themes have no owner)
    op.add_column('themes', sa.Column('user_id', sa.Integer(),
                  sa.ForeignKey('users.id'), nullable=True))
    op.create_index('idx_themes_user_id', 'themes', ['user_id'])


def downgrade() -> None:
    op.drop_index('idx_themes_user_id', table_name='themes')
    op.drop_column('themes', 'user_id')
    op.alter_column('pipeline_runs', 'character_id',
                    existing_type=sa.Integer(), nullable=True)
    op.alter_column('characters', 'user_id',
                    existing_type=sa.Integer(), nullable=True)
```

### Route Pattern: Catching PermissionError

```python
@router.get("/{slug}")
async def api_get_character(
    slug: str,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    repo = CharacterRepository(session)
    try:
        character = await repo.get_by_slug(slug, user=current_user)
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden")
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return character_to_detail(character)
```

### Discretion Recommendations

**1. Repos that need user_id parameter directly:**
- `CharacterRepository` -- Character.user_id is the source of truth
- `ThemeRepository` -- Theme.user_id (new column) for user themes

**2. Repos that derive ownership via character join:**
- `PipelineRunRepository` -- joins PipelineRun.character_id -> Character.user_id
- `ContentPackageRepository` -- joins ContentPackage.character_id -> Character.user_id
- `GeneratedImageRepository` -- joins GeneratedImage.character_id -> Character.user_id
- `BatchJobRepository` -- joins BatchJob.character_id -> Character.user_id
- `ScheduledPostRepository` -- joins ScheduledPost.character_id -> Character.user_id

**3. Repos that need NO changes:**
- `UsageRepository` -- already filters by user_id
- `UserRepository` -- users table is self-scoped

**4. AgentStat and TrendEvent:** Keep as-is. They're accessed through PipelineRun, which is already tenant-filtered. The pipeline_repo methods for these (get_agent_stats_for_run, get_trend_events_for_run) take pipeline_run_id, which is validated upstream. If a route needs agent stats, it first loads the pipeline run (with tenant check), then uses the run's id.

**5. Helper dependency:** YES, create `get_user_character()`. It's used by 20+ routes in characters.py plus routes in pipeline.py, content.py, jobs.py, publishing.py that operate on character-scoped resources. This is the highest-value DRY opportunity in this phase.

**6. 403 check implementation:** Use fetch-then-check for single-resource lookups (get_by_id, get_by_slug). Use query filtering for list operations (list_all, list_runs, etc.) -- lists just show the user's own data without raising 403.

## Repo Method Inventory

Complete list of repository methods needing user parameter:

### CharacterRepository (8 methods)
| Method | Change | Strategy |
|--------|--------|----------|
| `get_by_slug` | Add user param, ownership check | Fetch-then-check (403) |
| `get_by_id` | Add user param, ownership check | Fetch-then-check (403) |
| `list_all` | Add user param, WHERE filter | Query filter |
| `create` | Set user_id from current_user | Assign on create |
| `update` | Validate ownership before update | Via get_by_slug |
| `soft_delete` | Validate ownership before delete | Via get_by_slug |
| `exists` | Add user filter | Query filter |
| Ref methods (7) | Character already validated upstream | No change needed (character validated by route) |

### PipelineRunRepository (5 read methods)
| Method | Change | Strategy |
|--------|--------|----------|
| `get_by_run_id` | Add user param, join Character | Fetch-then-check (403) |
| `get_by_run_id_with_relations` | Add user param, join Character | Fetch-then-check (403) |
| `list_runs` | Add user param, join Character | Query filter |
| `count_runs` | Add user param, join Character | Query filter |
| Write methods (create_run, update_run, finish_run) | character_id required, validated upstream | No user check needed (character validated by route) |
| TrendEvent/WorkOrder/AgentStat methods | Accessed via pipeline_run_id | No change (transitively scoped) |

### ContentPackageRepository (6 read methods)
| Method | Change | Strategy |
|--------|--------|----------|
| `get_by_id` | Add user param, join Character | Fetch-then-check (403) |
| `list_packages` | Add user param, join Character | Query filter |
| `count` | Add user param, join Character | Query filter |
| `get_by_ids` | Add user param, join Character | Query filter |
| `get_by_id_with_character` | Add user param, check character | Fetch-then-check (403) |
| `get_for_run` | Pipeline run already validated | No change needed |
| `get_recent_topics` | Internal dedup, no user context | No change (system operation) |

### GeneratedImageRepository (3 read methods)
| Method | Change | Strategy |
|--------|--------|----------|
| `get_by_id` | Add user param, join Character | Fetch-then-check (403) |
| `list_images` | Add user param, join Character | Query filter |
| `count` | Add user param, join Character | Query filter |

### BatchJobRepository (3 read methods)
| Method | Change | Strategy |
|--------|--------|----------|
| `get_by_job_id` | Add user param, join Character | Fetch-then-check (403) |
| `list_jobs` | Add user param, join Character | Query filter |
| `count` | Add user param, join Character | Query filter |

### ThemeRepository (6 methods)
| Method | Change | Strategy |
|--------|--------|----------|
| `get_by_id` | Add user param | Fetch-then-check (403) |
| `get_by_key` | Add user param | Fetch-then-check (403) |
| `list_global` | No change | Global themes visible to all |
| `list_for_character` | Character already validated upstream | No change |
| `list_effective` | Add user param for user themes | Query filter (global + user's own) |
| `create` | Accept user_id for user themes | Assign on create |

### ScheduledPostRepository (5 read methods)
| Method | Change | Strategy |
|--------|--------|----------|
| `get_by_id` | Add user param, join Character | Fetch-then-check (403) |
| `list_posts` | Add user param, join Character | Query filter |
| `count` | Add user param, join Character | Query filter |
| `get_due_posts` | System scheduler operation | No change (internal) |
| `get_posts_by_date_range` | Add user param, join Character | Query filter |
| `get_queue_summary` | Add user param, join Character | Query filter |

## Route Inventory

All routes already have `current_user=Depends(get_current_user)`. Changes needed:

| Route File | Routes | Change Needed |
|------------|--------|---------------|
| `characters.py` | 19 routes | Pass current_user to repo methods |
| `pipeline.py` | ~12 routes | Pass current_user to repo methods |
| `content.py` | ~10 routes | Pass current_user to repo methods |
| `generation.py` | 3 routes | Already uses current_user for key selection; add character ownership check |
| `themes.py` | 6 routes | Pass current_user to repo methods |
| `jobs.py` | 4 routes | Pass current_user to repo methods |
| `publishing.py` | 7 routes | Pass current_user to repo methods |
| `agents.py` | 6 routes | Consider admin-only or keep user-scoped (monitoring data) |
| `drive.py` | 5 routes | Pass current_user to repo methods |
| `auth.py` | 5 routes | No change (exempt from tenant filtering) |

**Exempt routes (no auth needed):**
- `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout` -- public auth endpoints
- `/health` -- system health check
- `/docs`, `/openapi.json` -- Swagger UI (FastAPI built-in)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No tenant filtering | All repos filter by user | Phase 13 | Every query scoped |
| Character.user_id nullable | Character.user_id NOT NULL | Phase 13 migration | DB-level ownership enforcement |
| PipelineRun.character_id nullable | PipelineRun.character_id NOT NULL | Phase 13 migration | Every run belongs to a character |
| Themes: global + character only | Themes: global + user + character | Phase 13 | Users can create custom themes |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `tests/` directory, imports from `src.api.app` |
| Quick run command | `python -m pytest tests/test_tenant.py -x` |
| Full suite command | `python -m pytest tests/ -x` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TENANT-01 | User sees only own characters, runs, images | integration | `python -m pytest tests/test_tenant.py::test_user_isolation -x` | Wave 0 |
| TENANT-02 | Repos filter by user_id via character join | integration | `python -m pytest tests/test_tenant.py::test_repo_filtering -x` | Wave 0 |
| TENANT-03 | Admin sees all data | integration | `python -m pytest tests/test_tenant.py::test_admin_bypass -x` | Wave 0 |
| TENANT-04 | Cross-user access returns 403 | integration | `python -m pytest tests/test_tenant.py::test_403_forbidden -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_tenant.py -x`
- **Per wave merge:** `python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_tenant.py` -- covers TENANT-01 through TENANT-04 with two-user setup
- [ ] Test fixtures: create two users (admin + regular), two characters (one per user), seed child data per character
- [ ] Framework already installed (pytest, pytest-asyncio, httpx) -- no new dependencies

## Open Questions

1. **Agent routes scoping**
   - What we know: Agent routes (list_agents, fetch_from_agent, trends_feed, trends_search) operate on monitoring/trends data that's mostly stateless (RSS feeds, in-memory cache)
   - What's unclear: Whether these should be admin-only or available to all authenticated users
   - Recommendation: Keep available to all authenticated users (trends are global data, not user-owned). Agent stats are already scoped via pipeline_run_id. The agents routes don't access any tenant-scoped tables directly.

2. **Drive routes file-system scoping**
   - What we know: Drive routes serve files from the filesystem (generated images). Currently they list/serve any file from the output directory.
   - What's unclear: Whether file serving should check ownership (images on disk aren't tagged with user_id)
   - Recommendation: For now, keep filesystem routes as-is (they serve generated images by filename). The DB-level tenant filtering prevents users from discovering other users' image IDs through API list endpoints. Direct filename access is acceptable since filenames are UUIDs and not guessable. Full filesystem isolation is a future concern.

## Sources

### Primary (HIGH confidence)
- Direct codebase analysis: `src/database/models.py`, all repository files, all route files
- CONTEXT.md decisions D-01 through D-10

### Secondary (MEDIUM confidence)
- SQLAlchemy 2.0 async patterns -- verified against existing codebase usage (project already uses these patterns successfully)
- Alembic migration patterns -- verified against existing migrations (001-009)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new libraries needed, pure refactoring of existing code
- Architecture: HIGH - decisions are locked, patterns are clear, codebase is well-understood
- Pitfalls: HIGH - identified from direct code analysis (background tasks, migration ordering, theme model)

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable -- no external dependencies changing)
