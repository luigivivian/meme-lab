"""Tests for static fallback when both Gemini tiers exhausted (Phase 10 -- QUOT-06)."""
import os
os.environ["GOOGLE_API_KEY"] = "test-free-key"
os.environ["GOOGLE_API_KEY_PAID"] = "test-paid-key"

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.key_selector import KeyResolution


@pytest.fixture
def mock_work_order():
    """Create a mock WorkOrder with all required fields."""
    trend_event = MagicMock()
    trend_event.source = "google_trends"
    trend_event.title = "test trend"
    trend_event.url = "https://example.com"
    trend_event.fetched_at = None

    wo = MagicMock()
    wo.situacao_key = "sabedoria"
    wo.order_id = "test-001"
    wo.trend_event = trend_event
    wo.gandalf_topic = "test"
    wo.humor_angle = "ironic"
    wo.relevance_score = 0.8
    wo.layout = "bottom"
    wo.phrases_count = 1
    wo.carousel_count = 1
    return wo


@pytest.fixture
def mock_backgrounds():
    return ["bg1.jpg", "bg2.jpg", "bg3.jpg"]


@pytest.mark.asyncio
@patch("src.pipeline.workers.image_worker.event_to_trend_item", return_value=MagicMock())
@patch("src.pipeline.workers.image_worker.create_image", return_value="/tmp/composed.jpg")
@patch("src.pipeline.workers.image_worker.ContentGenerator")
async def test_compose_static_on_exhaustion(
    mock_gen_cls, mock_create_image, mock_eti, mock_work_order, mock_backgrounds
):
    """When resolve() returns tier='exhausted', compose() returns static background without calling _try_gemini."""
    mock_gen_cls.return_value.backgrounds = mock_backgrounds

    with patch(
        "src.services.key_selector.UsageAwareKeySelector.resolve",
        new_callable=AsyncMock,
        return_value=KeyResolution(api_key="", tier="exhausted", mode="auto"),
    ):
        from src.pipeline.workers.image_worker import ImageWorker

        worker = ImageWorker(background_mode="auto")
        result = await worker.compose(
            "test phrase", mock_work_order, user_id=1, session=MagicMock()
        )

    assert result.background_source == "static"
    assert result.image_path == "/tmp/composed.jpg"
    assert result.background_path in mock_backgrounds


@pytest.mark.asyncio
@patch("src.pipeline.workers.image_worker.event_to_trend_item", return_value=MagicMock())
@patch("src.pipeline.workers.image_worker.create_image", return_value="/tmp/composed.jpg")
@patch("src.pipeline.workers.image_worker.ContentGenerator")
async def test_metadata_on_exhaustion(
    mock_gen_cls, mock_create_image, mock_eti, mock_work_order, mock_backgrounds
):
    """ComposeResult.image_metadata contains fallback_reason='quota_exhausted' on exhaustion."""
    mock_gen_cls.return_value.backgrounds = mock_backgrounds

    with patch(
        "src.services.key_selector.UsageAwareKeySelector.resolve",
        new_callable=AsyncMock,
        return_value=KeyResolution(api_key="", tier="exhausted", mode="auto"),
    ):
        from src.pipeline.workers.image_worker import ImageWorker

        worker = ImageWorker(background_mode="auto")
        result = await worker.compose(
            "test phrase", mock_work_order, user_id=1, session=MagicMock()
        )

    assert result.image_metadata["fallback_reason"] == "quota_exhausted"


@pytest.mark.asyncio
@patch("src.pipeline.workers.image_worker.event_to_trend_item", return_value=MagicMock())
@patch("src.pipeline.workers.image_worker.create_image", return_value="/tmp/composed.jpg")
@patch("src.pipeline.workers.image_worker.ContentGenerator")
async def test_compose_no_auth_backward_compat(
    mock_gen_cls, mock_create_image, mock_eti, mock_work_order, mock_backgrounds
):
    """compose() without user_id/session works as before -- no pre-check, static mode."""
    mock_gen_cls.return_value.backgrounds = mock_backgrounds

    from src.pipeline.workers.image_worker import ImageWorker

    worker = ImageWorker(background_mode="static")
    result = await worker.compose("test", mock_work_order)

    assert result.background_source == "static"
    assert result.image_path != ""


@pytest.mark.asyncio
@patch("src.pipeline.workers.image_worker.event_to_trend_item", return_value=MagicMock())
@patch("src.pipeline.workers.image_worker.create_image", return_value="/tmp/composed.jpg")
@patch("src.pipeline.workers.image_worker.ContentGenerator")
async def test_fallback_reason_generation_failed(
    mock_gen_cls, mock_create_image, mock_eti, mock_work_order, mock_backgrounds
):
    """When Gemini fails and static fallback catches, fallback_reason='generation_failed'."""
    mock_gen_cls.return_value.backgrounds = mock_backgrounds

    from src.pipeline.workers.image_worker import ImageWorker

    worker = ImageWorker(background_mode="gemini")

    with patch.object(worker, "_try_gemini", new_callable=AsyncMock, return_value=(None, "static", {})):
        result = await worker.compose("test", mock_work_order)

    assert result.background_source == "static"
    assert result.image_metadata.get("fallback_reason") == "generation_failed"


@pytest.mark.asyncio
@patch("src.pipeline.workers.image_worker.event_to_trend_item", return_value=MagicMock())
@patch("src.pipeline.workers.image_worker.create_image", return_value="/tmp/composed.jpg")
@patch("src.pipeline.workers.image_worker.ContentGenerator")
async def test_fallback_reason_mode_static(
    mock_gen_cls, mock_create_image, mock_eti, mock_work_order, mock_backgrounds
):
    """When background_mode='static', fallback_reason='mode_static'."""
    mock_gen_cls.return_value.backgrounds = mock_backgrounds

    from src.pipeline.workers.image_worker import ImageWorker

    worker = ImageWorker(background_mode="static")
    result = await worker.compose("test", mock_work_order)

    assert result.image_metadata.get("fallback_reason") == "mode_static"
