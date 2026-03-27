# Phase 13: Tenant Isolation - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Every user sees only their own data across all resources (characters, pipeline runs, content packages, generated images, batch jobs, scheduled posts). Admin users can bypass isolation to access all users' data. All routes (except /auth/*, /health, /docs) require authentication. Cross-user data access returns 403 Forbidden; truly missing resources return 404.

</domain>

<decisions>
## Implementation Decisions

### Scoping Strategy
- **D-01:** Transitive ownership via character — PipelineRun, ContentPackage, GeneratedImage, BatchJob, ScheduledPost, WorkOrder are owned by character, which has user_id. Repos join through character to filter by user. No new user_id columns needed on child tables.
- **D-02:** PipelineRun.character_id becomes required (non-nullable). Every run must belong to a character. Orphan runs are not allowed.
- **D-03:** Theme ownership is global + user themes. Global themes (no user_id) visible to all. Users can create their own themes via a new user_id column on Theme. Repos return global + user's own themes. Admin can manage global themes.
- **D-04:** 403 for accessing another user's data, 404 for truly non-existent resources. Standard REST semantics — reveals existence but enforces isolation.

### Enforcement Layer
- **D-05:** Enforcement at repository level. All repo methods take user_id parameter and filter by it. Routes pass current_user.id to repos. Repos are the single enforcement point.
- **D-06:** All routes require authentication. Every route except /auth/*, /health, and /docs injects get_current_user. This activates the deferred AUTH-05 from Phase 4. Unauthenticated requests get 401.
- **D-07:** Admin bypass via role check in repos. If user.role == "admin", repos skip user_id filtering and return all data. No extra headers, query params, or separate endpoints needed. Admin always sees everything.

### Existing Data Migration
- **D-08:** Assign all existing data to seed admin (user id=1). Migration backfills all characters with null user_id to admin. PipelineRuns with null character_id get assigned to default character (mago-mestre).
- **D-09:** Character.user_id becomes NOT NULL after backfill. Enforces ownership at DB level — impossible to create orphan characters.
- **D-10:** PipelineRun.character_id becomes NOT NULL after backfill. Consistent with D-02 — every run belongs to a character, which belongs to a user.

### Claude's Discretion
- Which repos need a dedicated `user_id` parameter vs which can derive ownership through joins
- Whether to add a helper dependency like `get_user_character()` that validates character ownership in one call
- Exact migration ordering and Alembic revision chaining
- How AgentStat and TrendEvent are handled (monitoring data, may remain global or scoped to pipeline run)
- Implementation of the 403 check — whether to fetch-then-check or use query filtering

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Auth Infrastructure (from Phase 3)
- `src/api/deps.py` — `get_current_user()` dependency, returns User ORM object with id, email, role
- `src/auth/jwt.py` — JWT verification utilities (verify_access_token)
- `.planning/phases/03-auth-backend/03-CONTEXT.md` — Auth decisions: JWT strategy, roles (admin/user), token lifetimes

### Route Protection Context (from Phase 4)
- `.planning/phases/04-route-protection/04-CONTEXT.md` — Phase 4 was SKIPPED; AUTH-05 deferred to "production or multi-tenant" — Phase 13 activates this

### Database Models & Repositories
- `src/database/models.py` — All ORM models; Character.user_id (line 76-78), User.role (line 517)
- `src/database/repositories/character_repo.py` — CharacterRepository (no user filter currently)
- `src/database/repositories/pipeline_repo.py` — PipelineRunRepository (character_id filter only)
- `src/database/repositories/content_repo.py` — ContentPackageRepository + GeneratedImageRepository
- `src/database/repositories/job_repo.py` — BatchJobRepository (no filter)
- `src/database/repositories/theme_repo.py` — ThemeRepository (global + per-character)
- `src/database/repositories/schedule_repo.py` — ScheduledPostRepository
- `src/database/repositories/usage_repo.py` — UsageRepository (already correctly user-scoped)

### API Routes (10 modules needing auth injection)
- `src/api/routes/characters.py` — 19 routes, character CRUD
- `src/api/routes/pipeline.py` — Manual run, status, approve/reject
- `src/api/routes/content.py` — Content packages, generated images
- `src/api/routes/generation.py` — Image generation (already uses current_user)
- `src/api/routes/themes.py` — Theme CRUD
- `src/api/routes/jobs.py` — Batch jobs
- `src/api/routes/publishing.py` — Scheduled posts
- `src/api/routes/agents.py` — Agent monitoring (may stay admin-only)
- `src/api/routes/drive.py` — File upload/download
- `src/api/routes/auth.py` — Auth routes (exempt from protection)

### Requirements
- `.planning/REQUIREMENTS.md` — TENANT-01 through TENANT-04

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `get_current_user` in `src/api/deps.py` — Ready to inject into all routes, returns User with id, email, role
- `UserRepository` in `src/database/repositories/user_repo.py` — Already correctly scoped
- `UsageRepository` in `src/database/repositories/usage_repo.py` — Already filters by user_id (model pattern)
- Character.user_id FK and `owner` relationship already exist in models.py

### Established Patterns
- All route modules use `Depends(db_session)` — same injection style for `Depends(get_current_user)`
- Repository pattern: class methods take session + filter params, return ORM objects
- Migration pattern: Alembic versions in `src/database/migrations/versions/`
- Error handling: `HTTPException(status_code=N, detail="message")`

### Integration Points
- Every repo method needs `user_id` parameter added (or `user: User` object for admin role checking)
- Every route handler needs `current_user: User = Depends(get_current_user)` added
- Theme model needs `user_id` FK column added (nullable — global themes have no owner)
- Migration: backfill Character.user_id, PipelineRun.character_id, then alter to NOT NULL
- Frontend: API calls need Authorization header (may already be handled by existing auth interceptor)

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches for tenant isolation implementation.

</specifics>

<deferred>
## Deferred Ideas

- **Admin bypass mechanism** — User chose the simplest approach (role check in repos). If more granular admin access needed later (e.g., "view as user X"), can add X-Admin-As-User header in a future phase.

</deferred>

---

*Phase: 13-tenant-isolation*
*Context gathered: 2026-03-25*
