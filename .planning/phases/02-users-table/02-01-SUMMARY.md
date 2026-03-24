---
phase: 02-users-table
plan: 01
subsystem: database
tags: [auth, users, migration, seed, bcrypt]
dependency_graph:
  requires: []
  provides: [User ORM model, migration 006, seed_admin_user]
  affects: [src/database/models.py, src/database/seed.py, characters table]
tech_stack:
  added: [bcrypt>=5.0.0]
  patterns: [TimestampMixin inheritance, nullable FK for multi-tenant prep, idempotent seed]
key_files:
  created:
    - src/database/migrations/versions/006_add_users_table.py
    - tests/test_users_table.py
  modified:
    - src/database/models.py
    - src/database/seed.py
    - requirements.txt
decisions:
  - "Migration 006 chains from 003 (not 005) because 004/005 are untracked files not committed to the branch"
  - "User model placed as section 11 at end of models.py to avoid disrupting existing model ordering"
  - "bcrypt bytes-to-str decode applied for MySQL VARCHAR storage compatibility"
metrics:
  duration_seconds: 202
  completed: "2026-03-24T02:19:30Z"
  tasks_completed: 2
  tasks_total: 2
  files_changed: 5
---

# Phase 02 Plan 01: Users Table and Seed Admin Summary

User ORM model with 9 data columns + timestamps, Alembic migration 006 creating users table and characters.user_id FK, bcrypt-hashed admin seed from env vars, 5 model-level tests.

## Task Results

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | User model, Character FK, bcrypt dependency, and test scaffold | `88ad263` (RED), `7cee034` (GREEN) | src/database/models.py, requirements.txt, tests/test_users_table.py |
| 2 | Alembic migration 006 and seed admin function | `a3e9b57` | src/database/migrations/versions/006_add_users_table.py, src/database/seed.py |

## What Was Built

### User Model (src/database/models.py)
- `class User(TimestampMixin, Base)` with `__tablename__ = "users"`
- Columns: id (PK), email (unique, String 255), hashed_password (String 200), role (String 20, default "user"), is_active (Boolean, default True), display_name (String 200, nullable), gemini_free_key (Text, nullable), gemini_paid_key (Text, nullable), active_key_tier (String 20, default "free"), created_at, updated_at
- Indexes: idx_users_role, idx_users_is_active (email gets unique index automatically)
- Relationship: `characters` back_populates Character.owner

### Character FK (src/database/models.py)
- Added `user_id: Mapped[Optional[int]]` with `ForeignKey("users.id")`, nullable
- Added `owner: Mapped[Optional["User"]]` relationship back_populates User.characters
- Existing characters unaffected (user_id remains NULL)

### Migration 006 (src/database/migrations/versions/006_add_users_table.py)
- Creates users table with all columns, PK, unique email constraint
- Creates idx_users_role and idx_users_is_active indexes
- Adds user_id column to characters with FK and idx_characters_user_id index
- Downgrade: drops FK/index from characters BEFORE dropping users table (correct ordering)
- Pure DDL -- no INSERT or data operations

### Seed Admin (src/database/seed.py)
- `seed_admin_user(session)` reads ADMIN_EMAIL and ADMIN_PASSWORD from env
- Normalizes email to lowercase (D-08)
- bcrypt.hashpw with gensalt, decoded to UTF-8 string for storage
- Idempotent: skips if admin already exists
- Integrated into run_seed() as step [4/4]

### Tests (tests/test_users_table.py)
- test_user_model_exists: importable, correct tablename
- test_users_columns: all 11 columns with correct types, defaults, nullable
- test_character_user_id_column: user_id exists, nullable, FK to users.id
- test_character_owner_relationship: Character has owner relationship
- test_user_characters_relationship: User has characters relationship

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Migration down_revision adjusted from '005' to '003'**
- **Found during:** Task 2
- **Issue:** Plan specified `down_revision = '005'` but migrations 004 and 005 do not exist in the committed codebase (they are untracked files in the main repo working directory, not committed to the `estrutura-agents` branch)
- **Fix:** Set `down_revision = '003'` which is the actual latest migration in the committed chain
- **Files modified:** src/database/migrations/versions/006_add_users_table.py

## Decisions Made

1. Migration 006 chains from revision 003 instead of 005 (004/005 not committed)
2. User model added as section 11 at end of models.py
3. bcrypt bytes decoded to UTF-8 string for MySQL VARCHAR(200) storage

## Verification Results

- `python -m pytest tests/test_users_table.py -x -v` -- 5/5 passed
- `python -c "from src.database.models import User; print(User.__tablename__)"` -- prints "users"
- `python -c "import bcrypt; print(bcrypt.__version__)"` -- prints 5.0.0
- Migration has 0 INSERT/session/seed operations (pure DDL)
- Migration downgrade order: drop FK from characters, then drop users table

## Known Stubs

None -- all functionality is fully wired.

## Self-Check: PASSED

All 6 files found. All 3 commits verified.
