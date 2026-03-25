"""Pydantic schemas for auth endpoints."""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    display_name: str | None = None

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    message: str


class ServiceUsage(BaseModel):
    service: str
    tier: str
    used: int
    limit: int
    remaining: int


class UsageResponse(BaseModel):
    services: list[ServiceUsage]
    resets_at: str


class CostStatsResponse(BaseModel):
    total_cost_usd: float
    total_images: int
    avg_cost_per_image: float
    days_tracked: int
