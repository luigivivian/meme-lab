---
phase: 14-instagram-connection-cdn
plan: 01
subsystem: backend
tags: [instagram, oauth, database, security, fernet]
dependency_graph:
  requires: []
  provides: [InstagramConnection-model, instagram-oauth-service, facebook-oauth-config]
  affects: [src/database/models.py, config.py]
tech_stack:
  added: [cryptography.fernet, httpx]
  patterns: [Fernet-encryption, Facebook-OAuth-flow, long-lived-token-refresh]
key_files:
  created:
    - src/database/migrations/versions/013_add_instagram_connections.py
    - src/services/instagram_oauth.py
  modified:
    - src/database/models.py
    - config.py
decisions:
  - Fernet symmetric encryption for Instagram access tokens at rest
  - Ephemeral key fallback with warning when INSTAGRAM_TOKEN_ENCRYPTION_KEY not set
  - Upsert pattern for exchange_code — deletes existing connection before creating new
  - Token refresh sets status to error on failure rather than deleting connection
metrics:
  duration: 3min
  completed: "2026-03-26T19:13:27Z"
---

# Phase 14 Plan 01: Instagram OAuth Foundation Summary

**InstagramConnection ORM model + migration 013 + config constants + InstagramOAuthService with Fernet encryption, token exchange, and bulk refresh**

## What Was Built

### Migration 013: instagram_connections table
- Columns: id, user_id (FK users.id CASCADE), ig_user_id, ig_username, page_id, access_token_encrypted (Text), token_expires_at, connected_at, status, created_at, updated_at
- Indexes: idx_ig_conn_user_id, idx_ig_conn_status
- UniqueConstraint: uq_ig_conn_user_ig on (user_id, ig_user_id)
- Down revision chains from 012

### InstagramConnection ORM model (section 15)
- Uses TimestampMixin + Base pattern consistent with all other models
- Status enum: active | expired | disconnected | error
- Relationship to User via `owner` back_populates `instagram_connections`

### Config constants
- FACEBOOK_APP_ID, FACEBOOK_APP_SECRET, FACEBOOK_OAUTH_REDIRECT_URI (env vars)
- FACEBOOK_GRAPH_API_VERSION = "v21.0", FACEBOOK_GRAPH_API_BASE computed
- INSTAGRAM_TOKEN_ENCRYPTION_KEY (env var for Fernet key)

### InstagramOAuthService
- `generate_auth_url()` — builds Facebook OAuth URL with CSRF state token, scopes: instagram_basic, instagram_content_publish, pages_show_list, pages_read_engagement
- `exchange_code(code, user_id)` — 5-step flow: code -> short-lived token -> long-lived token (60 days) -> find IG business account via Page -> encrypt and store
- `refresh_expiring_tokens(days_before_expiry=7)` — bulk query + refresh for tokens expiring within window, error handling per-connection
- `get_status(user_id)` — returns connection info dict or None
- `disconnect(user_id)` — sets status=disconnected, clears encrypted token
- `_encrypt_token` / `_decrypt_token` — Fernet symmetric encryption
- `InstagramOAuthError` exception with fb_error_code for Graph API errors

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | bdd883d | Migration 013, InstagramConnection model, config constants |
| 2 | 05b77c0 | InstagramOAuthService with encryption and refresh |

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. All methods are fully implemented with real Facebook Graph API integration (no mock data). The service requires valid FACEBOOK_APP_ID/SECRET env vars to actually work at runtime.

## Files

| File | Action | Purpose |
|------|--------|---------|
| src/database/migrations/versions/013_add_instagram_connections.py | Created | Alembic migration for instagram_connections table |
| src/database/models.py | Modified | Added InstagramConnection model (section 15) + User relationship |
| config.py | Modified | Added Facebook OAuth + Fernet encryption config constants |
| src/services/instagram_oauth.py | Created | Full OAuth service: auth URL, token exchange, encryption, refresh, status, disconnect |

## Self-Check: PASSED

All files exist. All commits verified.
