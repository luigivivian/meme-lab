"""Reels pipeline orchestrator — chains 5 modules sequentially with progress tracking.

Sequential steps:
1. Image generation (Gemini) -> list of 1080x1920 JPEGs
2. Script generation (Gemini multimodal) -> structured roteiro JSON
3. TTS narration (Gemini Flash TTS) -> WAV audio
4. Transcription (Gemini multimodal) -> SRT subtitles
5. Video assembly (FFmpeg xfade) -> final MP4

Per D-01: independent orchestrator in src/reels_pipeline/main.py.

Phase 999.4 — Instagram Reels Pipeline
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from src.reels_pipeline.config import (
    REELS_OUTPUT_DIR,
    REELS_USD_TO_BRL,
)

logger = logging.getLogger("clip-flow.reels.pipeline")


@dataclass
class ReelsResult:
    """Result of a complete reels pipeline run."""

    job_dir: str
    video_path: str
    script: dict
    image_paths: list[str]
    audio_path: str
    srt_path: str
    cost_usd: float
    cost_brl: float


class ReelsPipeline:
    """Sequential orchestrator for the 5-step Reels pipeline.

    Usage:
        pipeline = ReelsPipeline()
        result = await pipeline.run("motivacao matinal", character_id=1)
    """

    def __init__(self, config_override: dict | None = None):
        self.config = config_override or {}

    async def run(
        self,
        tema: str,
        character_id: int | None = None,
        on_progress: Callable[[str, int], None] | None = None,
    ) -> ReelsResult:
        """Run the full 5-step pipeline sequentially.

        Args:
            tema: Theme/topic for the reel.
            character_id: Optional character ID for image generation.
            on_progress: Optional callback (step: str, pct: int) -> None.

        Returns:
            ReelsResult with all artifact paths and cost tracking.
        """
        cost_usd = 0.0

        def _progress(step: str, pct: int):
            logger.info(f"Pipeline step: {step} ({pct}%)")
            if on_progress:
                on_progress(step, pct)

        # Setup: create job directory
        tema_slug = re.sub(r"[^a-z0-9]+", "_", tema.lower().strip())[:40]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_dir = os.path.join(REELS_OUTPUT_DIR, f"{timestamp}_{tema_slug}")
        images_dir = os.path.join(job_dir, "images")
        os.makedirs(images_dir, exist_ok=True)

        logger.info(f"Pipeline started: tema='{tema}', job_dir={job_dir}")

        # Step 1 - Images (0-20%)
        from src.reels_pipeline.image_gen import generate_reel_images

        image_paths = await generate_reel_images(
            tema=tema,
            character_id=character_id,
            output_dir=images_dir,
            count=self.config.get("image_count"),
            db_config=self.config,
        )
        _progress("images", 20)

        # Step 2 - Script (20-40%)
        from src.reels_pipeline.script_gen import generate_script

        script = await generate_script(
            image_paths=image_paths,
            tema=tema,
            config_override=self.config,
        )
        # Save roteiro JSON as artifact
        roteiro_path = os.path.join(job_dir, "roteiro.json")
        with open(roteiro_path, "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)
        cost_usd += 0.001  # Gemini script gen ~$0.001
        _progress("script", 40)

        # Step 3 - TTS (40-60%)
        from src.reels_pipeline.tts import estimate_tts_cost, generate_narration

        narration_text = script.get("narracao_completa", "")
        audio_path = os.path.join(job_dir, "audio.wav")
        await generate_narration(
            text=narration_text,
            output_path=audio_path,
            voice=self.config.get("tts_voice"),
            provider=self.config.get("tts_provider"),
        )
        cost_usd += estimate_tts_cost(narration_text)
        _progress("tts", 60)

        # Step 4 - Transcription (60-75%)
        from src.reels_pipeline.transcriber import (
            estimate_transcription_cost,
            transcribe_to_srt,
        )

        srt_path = os.path.join(job_dir, "subtitles.srt")
        await transcribe_to_srt(
            audio_path=audio_path,
            output_path=srt_path,
            language=self.config.get("script_language"),
            provider=self.config.get("transcription_provider"),
        )
        # Estimate audio duration from TTS text length (~150 chars/min)
        est_duration_s = max(len(narration_text) / 150 * 60, 10)
        cost_usd += estimate_transcription_cost(est_duration_s)
        _progress("transcription", 75)

        # Step 5 - Assembly (75-95%)
        from src.reels_pipeline.video_builder import build_reel_video

        video_path = os.path.join(job_dir, "final.mp4")
        build_reel_video(
            image_paths=image_paths,
            audio_path=audio_path,
            srt_path=srt_path,
            output_path=video_path,
            config_override=self.config,
        )
        _progress("assembly", 95)

        # Done (100%)
        cost_brl = cost_usd * REELS_USD_TO_BRL
        _progress("complete", 100)

        logger.info(
            f"Pipeline complete: video={video_path}, "
            f"cost=${cost_usd:.4f} / R${cost_brl:.4f}"
        )

        return ReelsResult(
            job_dir=job_dir,
            video_path=video_path,
            script=script,
            image_paths=image_paths,
            audio_path=audio_path,
            srt_path=srt_path,
            cost_usd=cost_usd,
            cost_brl=cost_brl,
        )
