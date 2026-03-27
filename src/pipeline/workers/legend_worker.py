"""LegendWorker — burns text overlay onto generated videos via FFmpeg.

Per D-09: Auto-trigger after video generation completes.
Per D-11: Graceful fallback on FFmpeg failure.
Per D-10: Output with _legend suffix preserving original.
"""

import asyncio
import logging

from config import VIDEO_LEGEND_ENABLED, VIDEO_LEGEND_MODE, WATERMARK_TEXT

logger = logging.getLogger("clip-flow.worker.legend")


class LegendWorker:
    """Burns meme phrase + watermark onto generated videos."""

    def __init__(self, renderer=None, mode: str | None = None):
        self._renderer = renderer
        self._mode = mode or VIDEO_LEGEND_MODE

    def _get_renderer(self):
        """Lazy-init renderer (avoid import if VIDEO_LEGEND_ENABLED=false)."""
        if self._renderer is None:
            from src.video_gen.legend_renderer import LegendRenderer
            self._renderer = LegendRenderer()
        return self._renderer

    async def process(self, video_path: str, phrase: str,
                      mode: str | None = None,
                      video_width: int = 1080,
                      video_height: int = 1350) -> str | None:
        """Process a video, returning legend video path or None on failure.

        Per D-11: Graceful fallback — returns None instead of raising.
        Per D-10: Output path has _legend suffix.
        """
        if not VIDEO_LEGEND_ENABLED:
            logger.debug("Legend rendering disabled (VIDEO_LEGEND_ENABLED=false)")
            return None

        renderer = self._get_renderer()
        if not renderer.is_available():
            logger.warning("FFmpeg not found — skipping legend render")
            return None

        output_path = renderer.legend_output_path(video_path)
        render_mode = mode or self._mode

        try:
            result = await asyncio.to_thread(
                renderer.render,
                video_path=video_path,
                output_path=output_path,
                phrase=phrase,
                watermark=WATERMARK_TEXT,
                mode=render_mode,
                video_width=video_width,
                video_height=video_height,
            )
            logger.info("Legend rendered: %s (mode=%s)", result, render_mode)
            return result
        except Exception as e:
            logger.error("Legend render failed (graceful fallback): %s", e)
            return None  # Per D-11
