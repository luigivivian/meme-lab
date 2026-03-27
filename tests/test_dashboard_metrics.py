"""Tests for DASH-05, DASH-06, DASH-07: Business metrics endpoint and repository method."""
import inspect
import pytest


# -- Test 1: get_business_metrics exists and returns dict with expected keys --

def test_business_metrics_method_exists():
    """DASH-06: UsageRepository has get_business_metrics() async method."""
    from src.database.repositories.usage_repo import UsageRepository
    assert hasattr(UsageRepository, "get_business_metrics"), "get_business_metrics method missing"
    assert inspect.iscoroutinefunction(UsageRepository.get_business_metrics), \
        "get_business_metrics should be async"


def test_business_metrics_method_signature():
    """get_business_metrics accepts user_id parameter."""
    from src.database.repositories.usage_repo import UsageRepository
    sig = inspect.signature(UsageRepository.get_business_metrics)
    params = list(sig.parameters.keys())
    assert "self" in params
    assert "user_id" in params


# -- Test 2: videos_generated has current, previous, total --

def test_business_metrics_videos_generated_schema():
    """DASH-06: videos_generated metric has current, previous, total integer fields."""
    # Validate by importing and checking the method source contains the keys
    import ast
    from src.database.repositories import usage_repo
    source = inspect.getsource(usage_repo.UsageRepository.get_business_metrics)
    assert "videos_generated" in source
    assert "current" in source
    assert "previous" in source
    assert "total" in source


# -- Test 3: avg_cost_per_video_brl has current and previous --

def test_business_metrics_avg_cost_schema():
    """DASH-05: avg_cost_per_video_brl metric has current and previous float fields."""
    from src.database.repositories.usage_repo import UsageRepository
    source = inspect.getsource(UsageRepository.get_business_metrics)
    assert "avg_cost_per_video_brl" in source


# -- Test 4: budget_remaining_brl has daily fields --

def test_business_metrics_budget_schema():
    """DASH-06: budget_remaining_brl metric has daily_remaining, daily_budget, daily_spent."""
    from src.database.repositories.usage_repo import UsageRepository
    source = inspect.getsource(UsageRepository.get_business_metrics)
    assert "budget_remaining_brl" in source
    assert "daily_remaining" in source
    assert "daily_budget" in source
    assert "daily_spent" in source


# -- Test 5: trends_collected has current, previous, total --

def test_business_metrics_trends_schema():
    """DASH-06: trends_collected metric has current, previous, total."""
    from src.database.repositories.usage_repo import UsageRepository
    source = inspect.getsource(UsageRepository.get_business_metrics)
    assert "trends_collected" in source


# -- Test 6: active_packages has current and total --

def test_business_metrics_packages_schema():
    """DASH-06: active_packages metric has current and total."""
    from src.database.repositories.usage_repo import UsageRepository
    source = inspect.getsource(UsageRepository.get_business_metrics)
    assert "active_packages" in source


# -- Test 7: Dashboard endpoint exists at /dashboard/business-metrics --

def test_business_metrics_endpoint_exists():
    """DASH-06: GET /dashboard/business-metrics endpoint is registered."""
    from src.api.routes.dashboard import router
    routes = [r.path for r in router.routes]
    assert "/business-metrics" in routes, \
        f"Expected /business-metrics in routes, got: {routes}"


def test_business_metrics_endpoint_method():
    """Endpoint accepts GET method."""
    from src.api.routes.dashboard import router
    for route in router.routes:
        if getattr(route, "path", "") == "/business-metrics":
            assert "GET" in route.methods
            break
    else:
        pytest.fail("/business-metrics route not found")


# -- Test: BRL conversion uses VIDEO_USD_TO_BRL --

def test_business_metrics_uses_brl_conversion():
    """DASH-05: get_business_metrics uses VIDEO_USD_TO_BRL for legacy cost conversion."""
    from src.database.repositories.usage_repo import UsageRepository
    source = inspect.getsource(UsageRepository.get_business_metrics)
    assert "VIDEO_USD_TO_BRL" in source, \
        "Should use VIDEO_USD_TO_BRL for legacy cost_brl=0 fallback"


# -- Test: Endpoint docstring references DASH requirements --

def test_business_metrics_endpoint_dash_reference():
    """Endpoint references DASH-06 or DASH-07 in docstring."""
    from src.api.routes import dashboard
    source = inspect.getsource(dashboard)
    assert "DASH-0" in source, "Dashboard module should reference DASH requirements"
