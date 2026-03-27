"""Tests for LegendWorker — async video legend processing.

Tests cover:
- LegendWorker.process() returns legend path on success
- LegendWorker.process() returns None when disabled
- LegendWorker.process() returns None when FFmpeg not available
- LegendWorker.process() returns None on FFmpeg failure (D-11 graceful fallback)
- LegendWorker.process() passes correct args to renderer
- LegendWorker.process() uses asyncio.to_thread for non-blocking execution
- Output path has _legend suffix
- LegendRequest / LegendBatchRequest Pydantic models validation
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── LegendWorker tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_process_returns_legend_path_on_success():
    """process() returns legend video path when renderer succeeds."""
    mock_renderer = MagicMock()
    mock_renderer.is_available.return_value = True
    mock_renderer.legend_output_path.return_value = "/output/video_legend.mp4"
    mock_renderer.render.return_value = "/output/video_legend.mp4"

    with patch("src.pipeline.workers.legend_worker.VIDEO_LEGEND_ENABLED", True):
        from src.pipeline.workers.legend_worker import LegendWorker

        worker = LegendWorker(renderer=mock_renderer)
        result = await worker.process(
            video_path="/input/video.mp4",
            phrase="Test phrase",
        )

    assert result == "/output/video_legend.mp4"
    mock_renderer.render.assert_called_once()


@pytest.mark.asyncio
async def test_process_returns_none_when_disabled():
    """process() returns None when VIDEO_LEGEND_ENABLED is False."""
    mock_renderer = MagicMock()

    with patch("src.pipeline.workers.legend_worker.VIDEO_LEGEND_ENABLED", False):
        from src.pipeline.workers.legend_worker import LegendWorker

        worker = LegendWorker(renderer=mock_renderer)
        result = await worker.process(
            video_path="/input/video.mp4",
            phrase="Test phrase",
        )

    assert result is None
    mock_renderer.render.assert_not_called()


@pytest.mark.asyncio
async def test_process_returns_none_when_ffmpeg_not_available():
    """process() returns None when FFmpeg is not installed."""
    mock_renderer = MagicMock()
    mock_renderer.is_available.return_value = False

    with patch("src.pipeline.workers.legend_worker.VIDEO_LEGEND_ENABLED", True):
        from src.pipeline.workers.legend_worker import LegendWorker

        worker = LegendWorker(renderer=mock_renderer)
        result = await worker.process(
            video_path="/input/video.mp4",
            phrase="Test phrase",
        )

    assert result is None
    mock_renderer.render.assert_not_called()


@pytest.mark.asyncio
async def test_process_returns_none_on_ffmpeg_failure():
    """process() returns None when FFmpeg fails (D-11 graceful fallback)."""
    mock_renderer = MagicMock()
    mock_renderer.is_available.return_value = True
    mock_renderer.legend_output_path.return_value = "/output/video_legend.mp4"
    mock_renderer.render.side_effect = RuntimeError("FFmpeg crashed")

    with patch("src.pipeline.workers.legend_worker.VIDEO_LEGEND_ENABLED", True):
        from src.pipeline.workers.legend_worker import LegendWorker

        worker = LegendWorker(renderer=mock_renderer)
        result = await worker.process(
            video_path="/input/video.mp4",
            phrase="Test phrase",
        )

    assert result is None  # Graceful fallback per D-11


@pytest.mark.asyncio
async def test_process_passes_correct_args_to_renderer():
    """process() passes WATERMARK_TEXT, mode, and video dimensions to renderer."""
    mock_renderer = MagicMock()
    mock_renderer.is_available.return_value = True
    mock_renderer.legend_output_path.return_value = "/output/video_legend.mp4"
    mock_renderer.render.return_value = "/output/video_legend.mp4"

    with (
        patch("src.pipeline.workers.legend_worker.VIDEO_LEGEND_ENABLED", True),
        patch("src.pipeline.workers.legend_worker.VIDEO_LEGEND_MODE", "fade"),
        patch("src.pipeline.workers.legend_worker.WATERMARK_TEXT", "@testhandle"),
    ):
        from src.pipeline.workers.legend_worker import LegendWorker

        worker = LegendWorker(renderer=mock_renderer, mode="fade")
        result = await worker.process(
            video_path="/input/video.mp4",
            phrase="Test phrase",
            video_width=1920,
            video_height=1080,
        )

    mock_renderer.render.assert_called_once_with(
        video_path="/input/video.mp4",
        output_path="/output/video_legend.mp4",
        phrase="Test phrase",
        watermark="@testhandle",
        mode="fade",
        video_width=1920,
        video_height=1080,
    )
    assert result == "/output/video_legend.mp4"


@pytest.mark.asyncio
async def test_process_uses_asyncio_to_thread():
    """process() wraps renderer.render in asyncio.to_thread for non-blocking execution."""
    mock_renderer = MagicMock()
    mock_renderer.is_available.return_value = True
    mock_renderer.legend_output_path.return_value = "/output/video_legend.mp4"
    mock_renderer.render.return_value = "/output/video_legend.mp4"

    with (
        patch("src.pipeline.workers.legend_worker.VIDEO_LEGEND_ENABLED", True),
        patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread,
    ):
        mock_to_thread.return_value = "/output/video_legend.mp4"
        from src.pipeline.workers.legend_worker import LegendWorker

        worker = LegendWorker(renderer=mock_renderer)
        result = await worker.process(
            video_path="/input/video.mp4",
            phrase="Test phrase",
        )

    mock_to_thread.assert_called_once()
    assert result == "/output/video_legend.mp4"


def test_legend_output_path_has_suffix():
    """Output path has _legend suffix preserving extension (D-10)."""
    from src.video_gen.legend_renderer import LegendRenderer

    output = LegendRenderer.legend_output_path("/path/to/video.mp4")
    assert output.endswith("_legend.mp4")
    assert "video_legend" in output


# ── Pydantic model tests ────────────────────────────────────────────────────


def test_legend_request_default_mode():
    """LegendRequest has default mode='static'."""
    from src.api.models import LegendRequest

    req = LegendRequest(content_package_id=1)
    assert req.content_package_id == 1
    assert req.mode == "static"


def test_legend_request_custom_mode():
    """LegendRequest accepts custom mode."""
    from src.api.models import LegendRequest

    req = LegendRequest(content_package_id=42, mode="fade")
    assert req.content_package_id == 42
    assert req.mode == "fade"


def test_legend_batch_request_validates_ids():
    """LegendBatchRequest accepts list of content_package_ids."""
    from src.api.models import LegendBatchRequest

    req = LegendBatchRequest(content_package_ids=[1, 2, 3])
    assert req.content_package_ids == [1, 2, 3]
    assert req.mode == "static"


def test_legend_batch_request_custom_mode():
    """LegendBatchRequest accepts custom mode applied to all."""
    from src.api.models import LegendBatchRequest

    req = LegendBatchRequest(content_package_ids=[10, 20], mode="typewriter")
    assert req.content_package_ids == [10, 20]
    assert req.mode == "typewriter"


# ── PostProductionLayer integration tests ────────────────────────────────────


def test_post_production_init_accepts_legend_worker():
    """PostProductionLayer.__init__ accepts legend_worker param."""
    from src.pipeline.workers.post_production import PostProductionLayer

    mock_legend = MagicMock()
    pp = PostProductionLayer(legend_worker=mock_legend)
    assert pp._legend_worker is mock_legend


def test_post_production_init_default_legend_worker_is_none():
    """PostProductionLayer.__init__ defaults legend_worker to None."""
    from src.pipeline.workers.post_production import PostProductionLayer

    pp = PostProductionLayer()
    assert pp._legend_worker is None


@pytest.mark.asyncio
async def test_safe_legend_calls_worker_process():
    """_safe_legend calls worker.process() and returns path on success."""
    from src.pipeline.workers.post_production import PostProductionLayer

    mock_worker = MagicMock()
    mock_worker.process = AsyncMock(return_value="/output/video_legend.mp4")

    pp = PostProductionLayer(legend_worker=mock_worker)

    pkg = MagicMock()
    pkg.video_path = "/input/video.mp4"
    pkg.phrase = "Test phrase"

    result = await pp._safe_legend(pkg)
    assert result == "/output/video_legend.mp4"
    mock_worker.process.assert_called_once_with(
        video_path="/input/video.mp4",
        phrase="Test phrase",
    )


@pytest.mark.asyncio
async def test_safe_legend_returns_none_on_failure():
    """_safe_legend returns None when worker fails (graceful fallback per D-11)."""
    from src.pipeline.workers.post_production import PostProductionLayer

    mock_worker = MagicMock()
    mock_worker.process = AsyncMock(side_effect=RuntimeError("FFmpeg crash"))

    pp = PostProductionLayer(legend_worker=mock_worker)

    pkg = MagicMock()
    pkg.video_path = "/input/video.mp4"
    pkg.phrase = "Test phrase"

    result = await pp._safe_legend(pkg)
    assert result is None


@pytest.mark.asyncio
async def test_safe_legend_returns_none_when_no_video_path():
    """_safe_legend returns None when package has no video_path."""
    from src.pipeline.workers.post_production import PostProductionLayer

    pp = PostProductionLayer()
    pkg = MagicMock()
    pkg.video_path = None
    pkg.phrase = "Test phrase"

    result = await pp._safe_legend(pkg)
    assert result is None


@pytest.mark.asyncio
async def test_safe_legend_lazy_creates_worker():
    """_safe_legend lazy-creates LegendWorker when none provided."""
    from src.pipeline.workers.post_production import PostProductionLayer

    pp = PostProductionLayer()  # No legend_worker provided
    assert pp._legend_worker is None

    pkg = MagicMock()
    pkg.video_path = "/input/video.mp4"
    pkg.phrase = "Test phrase"

    with patch("src.pipeline.workers.post_production.VIDEO_LEGEND_ENABLED", True):
        with patch("src.pipeline.workers.legend_worker.VIDEO_LEGEND_ENABLED", True):
            mock_renderer = MagicMock()
            mock_renderer.is_available.return_value = True
            mock_renderer.legend_output_path.return_value = "/output/video_legend.mp4"
            mock_renderer.render.return_value = "/output/video_legend.mp4"

            with patch("src.video_gen.legend_renderer.LegendRenderer", return_value=mock_renderer):
                result = await pp._safe_legend(pkg)

    # Worker was lazy-created and cached
    assert pp._legend_worker is not None


@pytest.mark.asyncio
async def test_enhance_calls_safe_legend_when_enabled_and_video_success():
    """enhance() calls _safe_legend when VIDEO_LEGEND_ENABLED=True and video_status='success'."""
    from src.pipeline.workers.post_production import PostProductionLayer

    mock_legend_worker = MagicMock()
    mock_legend_worker.process = AsyncMock(return_value="/output/video_legend.mp4")

    pp = PostProductionLayer(legend_worker=mock_legend_worker)
    pp._safe_caption = AsyncMock(return_value="caption")
    pp._safe_hashtags = AsyncMock(return_value=["#tag"])
    pp._safe_quality = AsyncMock(return_value=0.9)

    pkg = MagicMock()
    pkg.video_status = "success"
    pkg.video_path = "/input/video.mp4"
    pkg.phrase = "Test phrase"
    pkg.work_order = None

    with patch("src.pipeline.workers.post_production.VIDEO_LEGEND_ENABLED", True):
        results = await pp.enhance([pkg])

    assert len(results) == 1
    assert results[0].legend_status == "success"
    assert results[0].legend_path == "/output/video_legend.mp4"


@pytest.mark.asyncio
async def test_enhance_skips_legend_when_disabled():
    """enhance() skips legend when VIDEO_LEGEND_ENABLED=False."""
    from src.pipeline.workers.post_production import PostProductionLayer

    mock_legend_worker = MagicMock()
    mock_legend_worker.process = AsyncMock(return_value="/output/video_legend.mp4")

    pp = PostProductionLayer(legend_worker=mock_legend_worker)
    pp._safe_caption = AsyncMock(return_value="caption")
    pp._safe_hashtags = AsyncMock(return_value=["#tag"])
    pp._safe_quality = AsyncMock(return_value=0.9)

    pkg = MagicMock()
    pkg.video_status = "success"
    pkg.video_path = "/input/video.mp4"
    pkg.phrase = "Test phrase"
    pkg.work_order = None

    with patch("src.pipeline.workers.post_production.VIDEO_LEGEND_ENABLED", False):
        results = await pp.enhance([pkg])

    assert len(results) == 1
    mock_legend_worker.process.assert_not_called()


@pytest.mark.asyncio
async def test_enhance_skips_legend_when_video_not_success():
    """enhance() skips legend when video_status is not 'success'."""
    from src.pipeline.workers.post_production import PostProductionLayer

    mock_legend_worker = MagicMock()
    mock_legend_worker.process = AsyncMock(return_value="/output/video_legend.mp4")

    pp = PostProductionLayer(legend_worker=mock_legend_worker)
    pp._safe_caption = AsyncMock(return_value="caption")
    pp._safe_hashtags = AsyncMock(return_value=["#tag"])
    pp._safe_quality = AsyncMock(return_value=0.9)

    pkg = MagicMock()
    pkg.video_status = "failed"
    pkg.video_path = "/input/video.mp4"
    pkg.phrase = "Test phrase"
    pkg.work_order = None

    with patch("src.pipeline.workers.post_production.VIDEO_LEGEND_ENABLED", True):
        results = await pp.enhance([pkg])

    assert len(results) == 1
    mock_legend_worker.process.assert_not_called()
