# Phase 14: Instagram Connection & CDN - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning
**Mode:** Auto-generated (autonomous --auto, user decision: GCS as CDN)

<domain>
## Phase Boundary

Connect Instagram Business Account via Facebook Graph API OAuth flow. Use existing GCS bucket (meme-lab-bucket) as CDN for public image URLs — no Cloudflare R2 needed. Store OAuth tokens securely, handle token refresh, and provide endpoints for the frontend to initiate connection and check status.

</domain>

<decisions>
## Implementation Decisions

### CDN Strategy
- **D-01:** Use existing **GCS bucket (meme-lab-bucket)** as CDN. Already working for video generation. Skip Cloudflare R2 entirely — GCS signed URLs are sufficient.
- **D-02:** Public image URLs via GCS signed URLs (1-hour expiry) for Instagram Graph API. The API needs publicly accessible URLs to publish media.

### Instagram OAuth Flow
- **D-03:** Use **Facebook Login for Business** with Instagram Graph API permissions: `instagram_basic`, `instagram_content_publish`, `pages_show_list`, `pages_read_engagement`.
- **D-04:** OAuth redirect flow: frontend opens popup → Facebook OAuth → redirect back with code → backend exchanges for long-lived token (60 days) → store encrypted in DB.
- **D-05:** Token refresh: background job checks token expiry, refreshes before expiration. Store `token_expires_at` in DB.
- **D-06:** New DB table `instagram_connections` with: `user_id`, `ig_user_id`, `ig_username`, `page_id`, `access_token` (encrypted), `token_expires_at`, `connected_at`, `status`.

### API Endpoints
- **D-07:** `GET /instagram/auth-url` — returns Facebook OAuth URL for frontend popup
- **D-08:** `GET /instagram/callback` — handles OAuth redirect, exchanges code for token
- **D-09:** `GET /instagram/status` — returns connection status (connected/disconnected/expired)
- **D-10:** `POST /instagram/disconnect` — revokes token, removes connection
- **D-11:** `POST /instagram/upload-media` — uploads image to GCS, creates Instagram media container

### Frontend
- **D-12:** Settings/connection page with "Conectar Instagram" button, connection status card, disconnect option.

### Claude's Discretion
- Token encryption method (Fernet or similar)
- OAuth state parameter for CSRF protection
- Error handling for expired/revoked tokens
- Instagram API rate limiting strategy

</decisions>

<canonical_refs>
## Canonical References

### Instagram Graph API
- Facebook Graph API docs: https://developers.facebook.com/docs/instagram-api/
- Content Publishing: https://developers.facebook.com/docs/instagram-api/guides/content-publishing

### Existing Code
- `src/services/instagram_client.py` — existing publish_reel() method
- `src/video_gen/gcs_uploader.py` — GCS upload (reuse for CDN)
- `src/database/models.py` — User model for foreign key
- `config.py` — env var patterns

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `GCSUploader` — already handles upload + signed URL generation
- `instagram_client.py` — has publish methods (extend with OAuth)
- Alembic migration pattern — 012 is latest
- FastAPI OAuth patterns from auth module

### Integration Points
- `src/api/routes/` — new `instagram.py` route module
- `src/api/app.py` — register instagram router
- `config.py` — FACEBOOK_APP_ID, FACEBOOK_APP_SECRET env vars
- `memelab/src/app/(app)/` — new settings or publishing page section

</code_context>

<specifics>
## Specific Ideas

- Reuse GCS bucket that's already working for video generation
- Instagram Business Account OAuth requires a Facebook App — user will create one
- Long-lived tokens last 60 days — auto-refresh before expiry

</specifics>

<deferred>
## Deferred Ideas

- Cloudflare R2 CDN (not needed — GCS sufficient)
- Instagram Insights/Analytics (future phase)
- Multiple Instagram accounts per user

</deferred>

---

*Phase: 14-instagram-connection-cdn*
*Context gathered: 2026-03-26 via autonomous mode*
