"""Tests for CRED-01 through CRED-03: BRL cost tracking for video generation."""
import inspect
import pytest
from sqlalchemy import Float, String


# -- Task 1: Schema & cost helper tests --

def test_api_usage_cost_brl_column():
    """CRED-04: cost_brl column exists on ApiUsage (Float, server_default='0.0')."""
    from src.database.models import ApiUsage
    table = ApiUsage.__table__
    cols = {c.name: c for c in table.columns}
    assert "cost_brl" in cols, "cost_brl column missing"
    col = cols["cost_brl"]
    assert isinstance(col.type, Float), f"cost_brl should be Float, got {type(col.type)}"
    assert col.server_default is not None, "cost_brl should have server_default"
    assert col.nullable is False, "cost_brl should not be nullable"


def test_api_usage_model_column():
    """CRED-04: model column exists on ApiUsage (String(100), nullable=True)."""
    from src.database.models import ApiUsage
    table = ApiUsage.__table__
    cols = {c.name: c for c in table.columns}
    assert "model" in cols, "model column missing"
    col = cols["model"]
    assert isinstance(col.type, String), f"model should be String, got {type(col.type)}"
    assert col.type.length == 100, f"model should be String(100), got String({col.type.length})"
    assert col.nullable is True, "model should be nullable"


def test_api_usage_tier_length():
    """tier column should be String(100) to fit model IDs like 'hailuo/2-3-image-to-video-standard'."""
    from src.database.models import ApiUsage
    table = ApiUsage.__table__
    cols = {c.name: c for c in table.columns}
    col = cols["tier"]
    assert isinstance(col.type, String)
    assert col.type.length == 100, f"tier should be String(100), got String({col.type.length})"


def test_compute_cost_brl_from_config():
    """CRED-02: Known model returns prices_brl value for exact duration."""
    from config import compute_video_cost_brl
    # Hailuo Standard: 10s = R$2.62, 6s = R$1.31
    assert compute_video_cost_brl("hailuo/2-3-image-to-video-standard", 10) == 2.62
    assert compute_video_cost_brl("hailuo/2-3-image-to-video-standard", 6) == 1.31


def test_compute_cost_brl_closest_duration():
    """CRED-02: Duration not in prices_brl snaps to closest valid duration."""
    from config import compute_video_cost_brl
    # Hailuo Standard has {6: 1.31, 10: 2.62}
    # duration=7 is closer to 6 than 10, so should return 1.31
    result = compute_video_cost_brl("hailuo/2-3-image-to-video-standard", 7)
    assert result == 1.31
    # duration=9 is closer to 10 than 6, so should return 2.62
    result = compute_video_cost_brl("hailuo/2-3-image-to-video-standard", 9)
    assert result == 2.62


def test_compute_cost_brl_unknown_model():
    """CRED-02: Unknown model falls back to cost_usd * VIDEO_USD_TO_BRL."""
    from config import compute_video_cost_brl, VIDEO_COST_PER_SECOND, VIDEO_USD_TO_BRL
    result = compute_video_cost_brl("unknown-model-xyz", 10)
    expected = round(10 * VIDEO_COST_PER_SECOND * VIDEO_USD_TO_BRL, 2)
    assert result == expected


# -- Task 2: Repository, endpoint, and response model tests --

def test_credits_summary_schema():
    """CRED-03: VideoCreditsResponse has all required fields with correct types."""
    from src.api.models import VideoCreditsResponse, ModelCostBreakdown
    # Verify all fields exist by instantiation
    resp = VideoCreditsResponse(
        days=30,
        total_spent_brl=5.24,
        total_spent_usd=0.91,
        total_videos=2,
        avg_cost_brl=2.62,
        alltime_spent_brl=10.48,
        alltime_videos=4,
        models=[
            ModelCostBreakdown(
                model_id="hailuo/2-3-image-to-video-standard",
                model_name="Hailuo 2.3 Standard",
                count=2,
                total_brl=5.24,
                avg_brl=2.62,
            )
        ],
        failed_count=0,
        failed_zero_cost=True,
        daily_budget_brl=17.25,
        daily_spent_brl=2.62,
        daily_remaining_brl=14.63,
    )
    assert resp.days == 30
    assert resp.total_spent_brl == 5.24
    assert len(resp.models) == 1
    assert resp.models[0].model_id == "hailuo/2-3-image-to-video-standard"
    assert resp.failed_zero_cost is True


def test_increment_signature():
    """UsageRepository.increment() accepts cost_brl and model parameters."""
    from src.database.repositories.usage_repo import UsageRepository
    sig = inspect.signature(UsageRepository.increment)
    params = list(sig.parameters.keys())
    assert "cost_brl" in params, "increment() missing cost_brl parameter"
    assert "model" in params, "increment() missing model parameter"
    # Verify defaults
    assert sig.parameters["cost_brl"].default == 0.0
    assert sig.parameters["model"].default is None


def test_video_credits_response_fields():
    """VideoCreditsResponse serializes correctly with all fields."""
    from src.api.models import VideoCreditsResponse
    data = {
        "days": 7,
        "total_spent_brl": 0.0,
        "total_spent_usd": 0.0,
        "total_videos": 0,
        "avg_cost_brl": 0.0,
        "alltime_spent_brl": 0.0,
        "alltime_videos": 0,
        "models": [],
        "failed_count": 0,
        "failed_zero_cost": True,
        "daily_budget_brl": 17.25,
        "daily_spent_brl": 0.0,
        "daily_remaining_brl": 17.25,
    }
    resp = VideoCreditsResponse(**data)
    serialized = resp.model_dump()
    assert serialized["days"] == 7
    assert serialized["daily_budget_brl"] == 17.25
    assert serialized["models"] == []
    assert "total_spent_brl" in serialized
    assert "alltime_spent_brl" in serialized
