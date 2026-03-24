"""Auth routes — register, login, refresh, logout, me."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import db_session, get_current_user
from src.auth.schemas import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)
from src.auth.service import AuthService

logger = logging.getLogger("clip-flow.auth")

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: RegisterRequest, session: AsyncSession = Depends(db_session)):
    """Create a new user account (AUTH-01). Returns user info, no password."""
    service = AuthService(session)
    try:
        user = await service.register(
            email=body.email,
            password=body.password,
            display_name=body.display_name,
        )
        return UserResponse.model_validate(user)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, session: AsyncSession = Depends(db_session)):
    """Authenticate user, return access + refresh tokens (AUTH-02)."""
    service = AuthService(session)
    try:
        user, access_token, refresh_token = await service.login(
            email=body.email,
            password=body.password,
        )
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid email or password")


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, session: AsyncSession = Depends(db_session)):
    """Rotate refresh token, return new access + refresh tokens (AUTH-03)."""
    service = AuthService(session)
    try:
        access_token, refresh_token = await service.refresh(body.refresh_token)
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")


@router.post("/logout", response_model=MessageResponse)
async def logout(body: RefreshRequest, session: AsyncSession = Depends(db_session)):
    """Invalidate refresh token (AUTH-04)."""
    service = AuthService(session)
    deleted = await service.logout(body.refresh_token)
    if not deleted:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def me(current_user=Depends(get_current_user)):
    """Return current user profile (requires valid access token)."""
    return UserResponse.model_validate(current_user)
