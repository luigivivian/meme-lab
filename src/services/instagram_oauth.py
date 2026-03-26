"""Instagram OAuth service — Facebook OAuth flow for Instagram Business Account connection.

Phase 14: Handles token exchange, Fernet encryption at rest, and token refresh.

Flow:
1. generate_auth_url() -> Facebook OAuth URL with CSRF state token
2. exchange_code(code, user_id) -> short-lived -> long-lived token -> encrypted in DB
3. refresh_expiring_tokens(days_before_expiry) -> bulk refresh before 60-day expiry
4. get_status(user_id) -> connection status dict
5. disconnect(user_id) -> revoke and mark disconnected
"""

import base64
import logging
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import config
from src.database.models import InstagramConnection

logger = logging.getLogger("clip-flow.instagram-oauth")


class InstagramOAuthError(Exception):
    """Raised when a Facebook/Instagram Graph API call fails."""

    def __init__(self, message: str, fb_error_code: int | None = None):
        self.message = message
        self.fb_error_code = fb_error_code
        super().__init__(self.message)


class InstagramOAuthService:
    """Handles Facebook OAuth flow for Instagram Business Account connection.

    Flow per D-04:
    1. generate_auth_url() -> Facebook OAuth URL with state CSRF token
    2. exchange_code(code, state) -> short-lived token -> long-lived token -> encrypted in DB
    3. refresh_token(connection_id) -> refresh before 60-day expiry
    4. disconnect(user_id) -> revoke token, mark disconnected
    5. get_status(user_id) -> connection status
    """

    # OAuth scopes required for Instagram publishing
    SCOPES = "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement"

    # Long-lived token validity (Facebook: 60 days)
    TOKEN_VALIDITY_DAYS = 60

    def __init__(self, session: AsyncSession):
        self._session = session
        self._fernet = self._build_fernet()

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def generate_auth_url(self) -> dict:
        """Generate Facebook OAuth URL with CSRF state token.

        Returns:
            dict with 'auth_url' and 'state'. Caller must store 'state'
            in session/cookie for CSRF validation on callback.
        """
        state = secrets.token_urlsafe(32)
        params = (
            f"client_id={config.FACEBOOK_APP_ID}"
            f"&redirect_uri={config.FACEBOOK_OAUTH_REDIRECT_URI}"
            f"&scope={self.SCOPES}"
            f"&state={state}"
            f"&response_type=code"
        )
        auth_url = (
            f"https://www.facebook.com/{config.FACEBOOK_GRAPH_API_VERSION}"
            f"/dialog/oauth?{params}"
        )
        return {"auth_url": auth_url, "state": state}

    async def exchange_code(self, code: str, user_id: int) -> InstagramConnection:
        """Exchange OAuth authorization code for long-lived token and store connection.

        Steps:
        1. Exchange code for short-lived token
        2. Exchange short-lived for long-lived token (60 days)
        3. Discover Facebook Page with linked Instagram Business Account
        4. Fetch IG user info (id, username)
        5. Encrypt token and upsert InstagramConnection
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Step 1: code -> short-lived token
            short_token = await self._exchange_code_for_short_token(client, code)

            # Step 2: short-lived -> long-lived token
            long_token = await self._exchange_for_long_lived_token(client, short_token)

            # Step 3: find Facebook Page with Instagram Business Account
            page_id, ig_user_id = await self._find_instagram_business_account(client, long_token)

            # Step 4: get IG username
            ig_username = await self._get_ig_username(client, ig_user_id, long_token)

        # Step 5: encrypt and store
        encrypted_token = self._encrypt_token(long_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=self.TOKEN_VALIDITY_DAYS)

        # Upsert: delete existing connection for this user+ig_user_id, then create new
        existing = await self._session.execute(
            select(InstagramConnection).where(
                InstagramConnection.user_id == user_id,
                InstagramConnection.ig_user_id == ig_user_id,
            )
        )
        existing_conn = existing.scalar_one_or_none()
        if existing_conn:
            await self._session.delete(existing_conn)
            await self._session.flush()

        connection = InstagramConnection(
            user_id=user_id,
            ig_user_id=ig_user_id,
            ig_username=ig_username,
            page_id=page_id,
            access_token_encrypted=encrypted_token,
            token_expires_at=expires_at,
            status="active",
        )
        self._session.add(connection)
        await self._session.commit()
        await self._session.refresh(connection)

        logger.info(
            "Instagram connected: user_id=%d ig_username=%s ig_user_id=%s",
            user_id, ig_username, ig_user_id,
        )
        return connection

    async def refresh_expiring_tokens(self, days_before_expiry: int = 7) -> int:
        """Refresh all tokens expiring within the given window.

        Returns the count of successfully refreshed tokens.
        """
        threshold = datetime.now(timezone.utc) + timedelta(days=days_before_expiry)
        result = await self._session.execute(
            select(InstagramConnection).where(
                InstagramConnection.status == "active",
                InstagramConnection.token_expires_at < threshold,
            )
        )
        connections = result.scalars().all()

        if not connections:
            logger.info("No expiring tokens found within %d days", days_before_expiry)
            return 0

        refreshed = 0
        async with httpx.AsyncClient(timeout=30.0) as client:
            for conn in connections:
                try:
                    old_token = self._decrypt_token(conn.access_token_encrypted)
                    new_token = await self._exchange_for_long_lived_token(client, old_token)
                    conn.access_token_encrypted = self._encrypt_token(new_token)
                    conn.token_expires_at = datetime.now(timezone.utc) + timedelta(
                        days=self.TOKEN_VALIDITY_DAYS
                    )
                    refreshed += 1
                    logger.info(
                        "Token refreshed for ig_username=%s (user_id=%d)",
                        conn.ig_username, conn.user_id,
                    )
                except Exception as exc:
                    conn.status = "error"
                    logger.error(
                        "Failed to refresh token for ig_username=%s (user_id=%d): %s",
                        conn.ig_username, conn.user_id, exc,
                    )

        await self._session.commit()
        logger.info("Refreshed %d/%d expiring tokens", refreshed, len(connections))
        return refreshed

    async def get_status(self, user_id: int) -> dict | None:
        """Get the Instagram connection status for a user.

        Returns dict with connection info, or None if not connected.
        """
        result = await self._session.execute(
            select(InstagramConnection).where(
                InstagramConnection.user_id == user_id,
            )
        )
        conn = result.scalar_one_or_none()
        if not conn:
            return None

        return {
            "connected": conn.status == "active",
            "ig_username": conn.ig_username,
            "status": conn.status,
            "token_expires_at": conn.token_expires_at.isoformat() if conn.token_expires_at else None,
            "connected_at": conn.connected_at.isoformat() if conn.connected_at else None,
        }

    async def disconnect(self, user_id: int) -> bool:
        """Disconnect the Instagram account for a user.

        Sets status to 'disconnected' and clears the encrypted token.
        Returns True if a connection was found and disconnected.
        """
        result = await self._session.execute(
            select(InstagramConnection).where(
                InstagramConnection.user_id == user_id,
            )
        )
        conn = result.scalar_one_or_none()
        if not conn:
            return False

        conn.status = "disconnected"
        conn.access_token_encrypted = ""
        await self._session.commit()

        logger.info(
            "Instagram disconnected: user_id=%d ig_username=%s",
            user_id, conn.ig_username,
        )
        return True

    # ------------------------------------------------------------------
    # Token encryption (Fernet)
    # ------------------------------------------------------------------

    def _encrypt_token(self, plaintext: str) -> str:
        """Encrypt a token string using Fernet symmetric encryption.

        Returns base64-encoded ciphertext suitable for TEXT column storage.
        """
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def _decrypt_token(self, ciphertext: str) -> str:
        """Decrypt a Fernet-encrypted token string.

        Raises InstagramOAuthError if decryption fails (wrong key, corrupted data).
        """
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise InstagramOAuthError(
                "Failed to decrypt Instagram token — encryption key may have changed"
            ) from exc

    @staticmethod
    def _build_fernet() -> Fernet:
        """Build Fernet instance from configured encryption key.

        Priority:
        1. INSTAGRAM_TOKEN_ENCRYPTION_KEY env var (must be valid Fernet key)
        2. Fallback: generate a key and log a warning (NOT safe for production — tokens
           become unrecoverable after restart)
        """
        key = config.INSTAGRAM_TOKEN_ENCRYPTION_KEY
        if key:
            # Validate it's a proper Fernet key (url-safe base64, 32 bytes)
            try:
                return Fernet(key.encode("utf-8") if isinstance(key, str) else key)
            except (ValueError, Exception) as exc:
                logger.error("Invalid INSTAGRAM_TOKEN_ENCRYPTION_KEY: %s", exc)
                raise InstagramOAuthError(
                    "INSTAGRAM_TOKEN_ENCRYPTION_KEY is set but invalid — "
                    "must be a valid Fernet key (use Fernet.generate_key())"
                ) from exc

        # Fallback: generate ephemeral key (tokens lost on restart)
        logger.warning(
            "INSTAGRAM_TOKEN_ENCRYPTION_KEY not set — generating ephemeral key. "
            "Set this env var in production to persist encrypted tokens across restarts. "
            "Generate with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
        return Fernet(Fernet.generate_key())

    # ------------------------------------------------------------------
    # Facebook Graph API helpers
    # ------------------------------------------------------------------

    async def _exchange_code_for_short_token(
        self, client: httpx.AsyncClient, code: str
    ) -> str:
        """Exchange authorization code for short-lived access token."""
        url = f"{config.FACEBOOK_GRAPH_API_BASE}/oauth/access_token"
        params = {
            "client_id": config.FACEBOOK_APP_ID,
            "redirect_uri": config.FACEBOOK_OAUTH_REDIRECT_URI,
            "client_secret": config.FACEBOOK_APP_SECRET,
            "code": code,
        }

        resp = await client.get(url, params=params)
        data = self._handle_fb_response(resp, "exchange code for short-lived token")
        return data["access_token"]

    async def _exchange_for_long_lived_token(
        self, client: httpx.AsyncClient, short_token: str
    ) -> str:
        """Exchange short-lived token for long-lived token (60 days)."""
        url = f"{config.FACEBOOK_GRAPH_API_BASE}/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": config.FACEBOOK_APP_ID,
            "client_secret": config.FACEBOOK_APP_SECRET,
            "fb_exchange_token": short_token,
        }

        resp = await client.get(url, params=params)
        data = self._handle_fb_response(resp, "exchange for long-lived token")
        return data["access_token"]

    async def _find_instagram_business_account(
        self, client: httpx.AsyncClient, token: str
    ) -> tuple[str, str]:
        """Find the Facebook Page with a linked Instagram Business Account.

        Returns (page_id, ig_user_id).
        Raises InstagramOAuthError if no page with IG business account found.
        """
        url = f"{config.FACEBOOK_GRAPH_API_BASE}/me/accounts"
        params = {
            "access_token": token,
            "fields": "id,name,instagram_business_account",
        }

        resp = await client.get(url, params=params)
        data = self._handle_fb_response(resp, "list Facebook Pages")

        pages = data.get("data", [])
        for page in pages:
            ig_account = page.get("instagram_business_account")
            if ig_account:
                page_id = page["id"]
                ig_user_id = ig_account["id"]
                logger.info(
                    "Found IG business account: page=%s ig_user_id=%s",
                    page.get("name", page_id), ig_user_id,
                )
                return page_id, ig_user_id

        raise InstagramOAuthError(
            "No Facebook Page with linked Instagram Business Account found. "
            "Ensure you have a Facebook Page connected to an Instagram Business/Creator account.",
            fb_error_code=None,
        )

    async def _get_ig_username(
        self, client: httpx.AsyncClient, ig_user_id: str, token: str
    ) -> str:
        """Fetch the Instagram username for a given IG user ID."""
        url = f"{config.FACEBOOK_GRAPH_API_BASE}/{ig_user_id}"
        params = {
            "fields": "id,username",
            "access_token": token,
        }

        resp = await client.get(url, params=params)
        data = self._handle_fb_response(resp, "get IG username")
        return data.get("username", "")

    @staticmethod
    def _handle_fb_response(resp: httpx.Response, context: str) -> dict:
        """Parse Facebook API response, raising InstagramOAuthError on failure."""
        try:
            data = resp.json()
        except Exception:
            raise InstagramOAuthError(
                f"Facebook API returned non-JSON response during {context}: "
                f"status={resp.status_code}"
            )

        if resp.status_code != 200:
            error = data.get("error", {})
            fb_code = error.get("code")
            fb_message = error.get("message", str(data))
            raise InstagramOAuthError(
                f"Facebook API error during {context}: {fb_message}",
                fb_error_code=fb_code,
            )

        return data
