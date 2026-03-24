"""AuthService — register, login, refresh, logout business logic."""

import logging
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt import (
    create_access_token,
    create_refresh_token_value,
    hash_refresh_token,
    refresh_token_expires_at,
)
from src.database.models import RefreshToken, User
from src.database.repositories.user_repo import UserRepository

logger = logging.getLogger("clip-flow.auth")


class AuthService:
    """Handles registration, login, token refresh, and logout."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)

    # -- Register (AUTH-01) --------------------------------------------------

    async def register(self, email: str, password: str, display_name: str | None = None) -> User:
        """Create a new user with bcrypt-hashed password. Raises ValueError if email exists."""
        existing = await self.user_repo.get_by_email(email)
        if existing:
            raise ValueError("Email already registered")

        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12))
        user = await self.user_repo.create(
            email=email,
            hashed_password=hashed.decode("utf-8"),
            role="user",  # per D-07
        )
        if display_name:
            user.display_name = display_name
        await self.session.flush()
        logger.info(f"User registered: {email} (id={user.id})")
        return user

    # -- Login (AUTH-02) -----------------------------------------------------

    async def login(self, email: str, password: str) -> tuple[User, str, str]:
        """Authenticate user, return (user, access_token, refresh_token). Raises ValueError on failure."""
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise ValueError("Invalid email or password")
        if not user.is_active:
            raise ValueError("Account is deactivated")

        if not bcrypt.checkpw(password.encode("utf-8"), user.hashed_password.encode("utf-8")):
            raise ValueError("Invalid email or password")

        access_token = create_access_token(user.id, user.email, user.role)
        refresh_token = create_refresh_token_value()

        # Store hashed refresh token in DB (per D-01)
        db_token = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=refresh_token_expires_at(),
        )
        self.session.add(db_token)
        await self.session.flush()

        logger.info(f"User logged in: {user.email} (id={user.id})")
        return user, access_token, refresh_token

    # -- Refresh (AUTH-03) ---------------------------------------------------

    async def refresh(self, refresh_token: str) -> tuple[str, str]:
        """Rotate refresh token: invalidate old, issue new access+refresh. Raises ValueError on failure."""
        token_hash = hash_refresh_token(refresh_token)
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        db_token = result.scalar_one_or_none()

        if not db_token:
            raise ValueError("Invalid refresh token")

        if db_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
            # Expired — clean up
            await self.session.delete(db_token)
            await self.session.flush()
            raise ValueError("Refresh token expired")

        # Get user
        user = await self.user_repo.get_by_id(db_token.user_id)
        if not user or not user.is_active:
            await self.session.delete(db_token)
            await self.session.flush()
            raise ValueError("User not found or deactivated")

        # Delete old token (per D-03: rotate on use)
        await self.session.delete(db_token)

        # Issue new tokens
        new_access = create_access_token(user.id, user.email, user.role)
        new_refresh = create_refresh_token_value()
        new_db_token = RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(new_refresh),
            expires_at=refresh_token_expires_at(),
        )
        self.session.add(new_db_token)
        await self.session.flush()

        logger.info(f"Token refreshed for user: {user.email} (id={user.id})")
        return new_access, new_refresh

    # -- Logout (AUTH-04) ----------------------------------------------------

    async def logout(self, refresh_token: str) -> bool:
        """Invalidate a refresh token by deleting it from DB. Returns True if found and deleted."""
        token_hash = hash_refresh_token(refresh_token)
        result = await self.session.execute(
            delete(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        deleted = result.rowcount > 0
        if deleted:
            logger.info("Refresh token invalidated (logout)")
        return deleted
