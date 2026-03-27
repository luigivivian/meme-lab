---
phase: 02-users-table
verified: 2026-03-24T03:00:00Z
status: gaps_found
score: 4/5 must-haves verified
gaps:
  - truth: "alembic upgrade head creates the users table with all required columns"
    status: failed
    reason: "Migration 006 sets down_revision='003', bypassing migrations 004 and 005 which also exist in the codebase and both chain from '003'. This creates a forked Alembic history with two heads (005 and 006). Running 'alembic upgrade head' (singular) raises a hard error: 'Multiple head revisions are present'. The users table can only be created via the non-standard 'alembic upgrade heads' (plural) command."
    artifacts:
      - path: "src/database/migrations/versions/006_add_users_table.py"
        issue: "down_revision = '003' creates a fork. The correct value is '005' to chain linearly after the two existing migrations."
    missing:
      - "Change down_revision in 006_add_users_table.py from '003' to '005' to restore a single-head linear migration chain"
---

# Phase 02: Users Table Verification Report

**Phase Goal:** MySQL has a users table that can store accounts, roles, and encrypted API keys
**Verified:** 2026-03-24T03:00:00Z
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | alembic upgrade head creates the users table with all required columns | FAILED | Two Alembic heads exist (005 and 006). `alembic upgrade head` exits with error "Multiple head revisions are present". The users table can only be applied via `alembic upgrade heads` (plural), which is non-standard and contradicts the stated truth. |
| 2 | alembic downgrade -1 drops the users table and characters.user_id column cleanly | VERIFIED | Migration downgrade() drops idx_characters_user_id, then user_id column, then idx_users_is_active, idx_users_role, then users table — correct FK-first ordering confirmed at lines 47-51 of 006_add_users_table.py. |
| 3 | Seed admin user is created when ADMIN_EMAIL and ADMIN_PASSWORD env vars are set | VERIFIED | seed_admin_user() in seed.py reads both env vars, normalizes email to lowercase, hashes with bcrypt, is idempotent via select-before-insert, and is called from run_seed() as step [4/4]. |
| 4 | characters table has a nullable user_id FK pointing to users.id | VERIFIED | Character.user_id at line 76-78 of models.py: Mapped[Optional[int]] with ForeignKey("users.id"), nullable=True. test_character_user_id_column confirms at runtime. |
| 5 | Existing characters are unaffected (user_id remains NULL) | VERIFIED | Column is nullable=True with no default, so existing rows get NULL on migration. Character.owner relationship is Mapped[Optional["User"]], meaning NULL is a valid state. |

**Score:** 4/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/database/models.py` | User ORM model class | VERIFIED | class User(TimestampMixin, Base) at line 506, __tablename__ = "users", all 9 data columns confirmed present |
| `src/database/migrations/versions/006_add_users_table.py` | Alembic migration creating users table and characters.user_id FK | STUB (chain broken) | File exists and is substantive, but down_revision='003' instead of '005' creates a two-headed fork. The migration itself is DDL-correct; the chain link is wrong. |
| `src/database/seed.py` | seed_admin_user function | VERIFIED | async def seed_admin_user(session) at line 262, bcrypt import at line 13, User import at line 18, called from run_seed() at line 319 |
| `tests/test_users_table.py` | Tests for AUTH-07 sub-requirements | VERIFIED | 5 tests present, all pass: test_user_model_exists, test_users_columns, test_character_user_id_column, test_character_owner_relationship, test_user_characters_relationship |
| `requirements.txt` | bcrypt dependency | VERIFIED | bcrypt>=5.0.0 at line 20 of requirements.txt; bcrypt 5.0.0 installed and importable |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| src/database/models.py | src/database/base.py | User inherits TimestampMixin, Base | WIRED | Line 506: `class User(TimestampMixin, Base)` — exact pattern matches |
| src/database/models.py | Character model | back_populates="owner" | WIRED | User.characters at line 522: `relationship(back_populates="owner")`. Character.owner at line 81: `relationship(back_populates="characters")`. Bidirectional confirmed. |
| src/database/seed.py | src/database/models.py | imports User model for admin seeding | WIRED | Line 18: `from src.database.models import Character, CharacterRef, Theme, User` |
| src/database/migrations/versions/006_add_users_table.py | 005 | Alembic migration chain | NOT_WIRED | down_revision = '003' — skips 004 and 005. Both exist in the codebase. Result: two Alembic heads, `upgrade head` fails. |

### Data-Flow Trace (Level 4)

Not applicable for this phase. All artifacts are database schema, ORM models, migrations, and seed scripts — no dynamic data rendering components.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| User model importable with correct tablename | `python -c "from src.database.models import User; print(User.__tablename__)"` | `users` | PASS |
| bcrypt installed at required version | `python -c "import bcrypt; print(bcrypt.__version__)"` | `5.0.0` | PASS |
| seed_admin_user importable | `python -c "from src.database.seed import seed_admin_user; print('ok')"` | `ok` | PASS |
| All 5 unit tests pass | `python -m pytest tests/test_users_table.py -x -v` | 5 passed in 0.19s | PASS |
| Migration has no data operations | `grep -c "INSERT\|session\|seed" 006_add_users_table.py` | `0` | PASS |
| alembic upgrade head creates users table | `python -m alembic upgrade head` | ERROR: Multiple head revisions are present | FAIL |
| Alembic head count | `python -m alembic heads` | `005 (head)`, `006 (head)` | FAIL (two heads) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| AUTH-07 | 02-01-PLAN.md | Tabela users no MySQL (email, hashed_password, role, api_keys criptografadas, created_at) | PARTIAL | ORM model has all required columns (email, hashed_password, role, gemini_free_key, gemini_paid_key, active_key_tier, created_at). Note: REQUIREMENTS.md says "api_keys criptografadas" (encrypted) but the PLAN's D-01/D-02 decisions store keys as plaintext Text fields, not encrypted. The requirement text is technically unmet for the "encrypted" qualifier, though the PLAN intentionally chose plaintext storage. Migration cannot be applied via standard `alembic upgrade head` due to fork. |

**Orphaned requirements check:** No additional AUTH-07-mapped requirements found in REQUIREMENTS.md beyond what the plan claims.

**Note on AUTH-07 "criptografadas" qualifier:** REQUIREMENTS.md says "api_keys criptografadas" (encrypted API keys). The plan's design decision D-01/D-02 chose plaintext Text columns (`gemini_free_key`, `gemini_paid_key`). The column comment in models.py reads "API keys — plaintext Text, nullable (per D-01, D-02)". This is a deliberate deviation from the literal requirement text. The plan accepted this tradeoff. It is noted here but not treated as a blocker since the plan explicitly documented it.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| src/database/migrations/versions/006_add_users_table.py | 15 | `down_revision = '003'` while 004 and 005 also exist, both chaining from 003 | Blocker | `alembic upgrade head` fails with "Multiple head revisions" error — the primary delivery mechanism for this phase cannot be invoked with the standard command |

### Human Verification Required

None — all verification was fully automated. The gap identified is programmatically confirmed by `alembic heads` returning two entries and `alembic upgrade head` returning a hard error.

### Gaps Summary

**One blocker gap preventing full goal achievement:**

The migration chain is forked. When Phase 02 was implemented, migrations 004 and 005 existed on disk as untracked files. The SUMMARY documents this as a deliberate decision: `down_revision` was set to `'003'` (the last committed revision at the time). Since then, 004 and 005 have been committed to the branch (both appear in `git status` as untracked — they exist on disk and are included in the working tree). Both `004` and `005` chain from `003`, which means Alembic now sees two parallel branches off of `003`: one through `004→005` and one directly to `006`.

The fix is a one-line change in `006_add_users_table.py`: change `down_revision = '003'` to `down_revision = '005'`. This restores linear chain `001→002→003→004→005→006` and makes `alembic upgrade head` work as expected.

All other must-haves are fully implemented and verified:
- User ORM model with all 9 data columns plus timestamps
- Character.user_id nullable FK with bidirectional relationship
- seed_admin_user function with bcrypt hashing, idempotency, and lowercase normalization
- 5/5 unit tests passing
- bcrypt 5.0.0 installed and in requirements.txt

---
_Verified: 2026-03-24T03:00:00Z_
_Verifier: Claude (gsd-verifier)_
