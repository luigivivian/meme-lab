---
phase: 07-usage-tracking-table
plan: 01
subsystem: database
tags: [orm, migration, api-usage, quota-tracking]
dependency_graph:
  requires: [users-table, refresh-tokens-migration-007]
  provides: [api-usage-table, api-usage-model, usage-tracking-schema]
  affects: [phase-08-atomic-counter, phase-09-dual-key, phase-11-dashboard]
tech_stack:
  added: []
  patterns: [TimestampMixin, nullable-FK-SET-NULL, UniqueConstraint-for-upsert]
key_files:
  created:
    - src/database/migrations/versions/008_add_api_usage_table.py
    - tests/test_api_usage.py
  modified:
    - src/database/models.py
decisions:
  - DateTime (not Date) for date column — UTC storage, PT conversion in repository layer
  - user_id nullable with ondelete SET NULL — preserves usage records when user deleted
  - server_default="1" on usage_count — first insert = 1 API call
  - UniqueConstraint enables Phase 8 INSERT ON DUPLICATE KEY UPDATE pattern
metrics:
  duration_seconds: 123
  completed: "2026-03-24T17:23:46Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 2
  files_modified: 1
---

# Phase 07 Plan 01: ApiUsage Table and Migration Summary

ApiUsage ORM model (section 14) with 7 columns, nullable FK to users.id (SET NULL), UniqueConstraint for Phase 8 atomic upsert, DateTime date column for UTC storage, and Alembic migration 008 chaining from 007.

## Tasks Completed

### Task 1: ApiUsage model, User relationship, and schema tests (TDD)

**RED:** Wrote 7 schema validation tests in `tests/test_api_usage.py` covering model existence, column types/nullability, FK, UniqueConstraint, indexes, DateTime type, and User relationship. All 7 failed (ImportError: ApiUsage not found).

**GREEN:** Added `ApiUsage(TimestampMixin, Base)` model to `src/database/models.py` as section 14 with all 7 columns (id, user_id, service, tier, date, usage_count, status), FK to users.id (ondelete SET NULL), UniqueConstraint, 3 indexes, and bidirectional relationship with User. Updated docstring to 14 tabelas. All 7 tests passed.

**Commits:**
- `d16a585` — test(07-01): add failing tests (RED)
- `a197828` — feat(07-01): add ApiUsage model (GREEN)

### Task 2: Alembic migration 008 for api_usage table

Created `008_add_api_usage_table.py` with revision chain 008 -> 007. Migration creates api_usage table with all columns matching the ORM model, PrimaryKeyConstraint, UniqueConstraint, and 3 indexes. Downgrade drops indexes then table (reverse order). Verified revision chain and full test suite (69 passed).

**Commit:** `6bfb28c` — feat(07-01): add Alembic migration 008

## Verification Results

- 7/7 schema tests pass (`python -m pytest tests/test_api_usage.py -x -v`)
- 69/69 full test suite pass (no regressions)
- Migration revision chain: 008 -> 007 (verified)
- ApiUsage model columns match migration exactly

## Deviations from Plan

None -- plan executed exactly as written.

## Known Stubs

None -- all columns, constraints, indexes, and relationships are fully implemented.

## Self-Check: PASSED

All 4 files found. All 3 commits verified.
