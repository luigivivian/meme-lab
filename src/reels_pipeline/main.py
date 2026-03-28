"""Reels pipeline orchestrator — chains 5 modules sequentially with progress tracking.

Sequential steps:
1. Image generation (Gemini) -> list of 1080x1920 JPEGs
2. Script generation (Gemini multimodal) -> structured roteiro JSON
3. TTS narration (Gemini Flash TTS) -> WAV audio
4. Transcription (Gemini multimodal) -> SRT subtitles
5. Video assembly (FFmpeg xfade) -> final MP4

Per D-01: independent orchestrator in src/reels_pipeline/main.py.
Supports both full run() and per-step execution for interactive mode (D-02, D-05).

Phase 999.4/999.5 — Instagram Reels Pipeline
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

    Supports two modes:
    - Full: pipeline.run(tema) — runs all steps sequentially
    - Per-step: pipeline.run_step_X(...) — runs individual steps with explicit I/O

    Usage:
        pipeline = ReelsPipeline()
        result = await pipeline.run("motivacao matinal", character_id=1)

        # Or per-step:
        prompt_data = await pipeline.run_step_prompt("motivacao matinal")
        images = await pipeline.run_step_images("motivacao matinal", None, prompt_data["job_dir"], prompt_data["images_dir"])
    """

    def __init__(self, config_override: dict | None = None):
        self.config = config_override or {}

    def _make_job_dir(self, tema: str) -> tuple[str, str]:
        """Create and return (job_dir, images_dir) for a tema."""
        tema_slug = re.sub(r"[^a-z0-9]+", "_", tema.lower().strip())[:40]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_dir = os.path.join(REELS_OUTPUT_DIR, f"{timestamp}_{tema_slug}")
        images_dir = os.path.join(job_dir, "images")
        os.makedirs(images_dir, exist_ok=True)
        return job_dir, images_dir

    # ------------------------------------------------------------------
    # Per-step methods (interactive mode)
    # ------------------------------------------------------------------

    async def run_step_prompt(
        self, tema: str, character_id: int | None = None
    ) -> dict:
        """Step 1: Set up working directory for a new reel job.

        Args:
            tema: Theme/topic text for the reel.
            character_id: Optional character ID (passed through for downstream steps).

        Returns:
            dict with keys: text, job_dir, images_dir.
        """
        job_dir, images_dir = self._make_job_dir(tema)
        logger.info(f"Step prompt: tema='{tema}', job_dir={job_dir}")
        return {"text": tema, "job_dir": job_dir, "images_dir": images_dir}

    async def run_step_images(
        self,
        tema: str,
        character_id: int | None,
        job_dir: str,
        images_dir: str,
        image_index: int | None = None,
    ) -> list[str]:
        """Step 2: Generate reel images via Gemini.

        Args:
            tema: Theme/topic for the reel.
            character_id: Optional character for consistent style.
            job_dir: Job working directory.
            images_dir: Directory for output images.
            image_index: If set, regenerate only this single image index.

        Returns:
            List of image file paths.
        """
        from src.reels_pipeline.image_gen import generate_reel_images

        count = 1 if image_index is not None else self.config.get("image_count")
        image_paths = await generate_reel_images(
            tema=tema,
            character_id=character_id,
            output_dir=images_dir,
            count=count,
            db_config=self.config,
        )
        return image_paths

    async def run_step_images_per_cena(
        self,
        script: dict,
        character_id: int | None,
        job_dir: str,
        images_dir: str,
    ) -> list[str]:
        """Step 3 (v2): Generate per-cena images using script context. Per REELV2-02.

        Args:
            script: Approved script dict with cenas list.
            character_id: Optional character for consistent style.
            job_dir: Job working directory.
            images_dir: Directory for output images.

        Returns:
            List of image file paths (1 per cena).
        """
        from src.reels_pipeline.image_gen import generate_reel_images_per_cena

        cenas = script.get("cenas", [])
        if not cenas:
            raise ValueError("Script has no cenas for image generation")

        return await generate_reel_images_per_cena(
            cenas=cenas,
            character_id=character_id,
            output_dir=images_dir,
        )

    async def run_step_script(
        self,
        image_paths: list[str] | None = None,
        tema: str = "",
        job_dir: str = "",
        character_id: int | None = None,
    ) -> dict:
        """Step 2 (v2): Generate structured roteiro (script).

        Supports text-only mode (image_paths=None) for interactive pipeline
        where script generates before images, and multimodal mode when images
        are available (sequential pipeline).

        Args:
            image_paths: Optional paths to reel images. None for text-only.
            tema: Theme/topic text.
            job_dir: Job working directory (roteiro.json saved here).
            character_id: Optional character for persona-aware script.

        Returns:
            Script dict with cenas, narracao_completa, etc.
        """
        from src.reels_pipeline.image_gen import _load_character_context
        from src.reels_pipeline.script_gen import generate_script

        char_ctx = None
        if character_id:
            char_ctx = await _load_character_context(character_id)

        script = await generate_script(
            image_paths=image_paths,
            tema=tema,
            config_override=self.config,
            character_context=char_ctx,
        )
        roteiro_path = os.path.join(job_dir, "roteiro.json")
        with open(roteiro_path, "w", encoding="utf-8") as f:
            json.dump(script, f, ensure_ascii=False, indent=2)
        return script

    async def run_step_tts(
        self, narration_text: str, job_dir: str
    ) -> tuple[str, float]:
        """Step 4: Generate TTS narration audio.

        Args:
            narration_text: Full narration text to synthesize.
            job_dir: Job working directory (audio saved here).

        Returns:
            Tuple of (audio_path, cost_usd).
        """
        from src.reels_pipeline.tts import estimate_tts_cost, generate_narration

        audio_path = os.path.join(job_dir, "audio.wav")
        await generate_narration(
            text=narration_text,
            output_path=audio_path,
            voice=self.config.get("tts_voice"),
            provider=self.config.get("tts_provider"),
        )
        cost_usd = estimate_tts_cost(narration_text)
        return audio_path, cost_usd

    async def run_step_srt(
        self, audio_path: str, job_dir: str
    ) -> tuple[str, float]:
        """Step 5: Transcribe audio to SRT subtitles.

        Args:
            audio_path: Path to narration audio file.
            job_dir: Job working directory (SRT saved here).

        Returns:
            Tuple of (srt_path, cost_usd).
        """
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
        # Estimate duration from audio file size (~48kB/s for 24kHz 16-bit mono)
        try:
            audio_size = os.path.getsize(audio_path)
            est_duration_s = max(audio_size / 48000, 10)
        except OSError:
            est_duration_s = 30
        cost_usd = estimate_transcription_cost(est_duration_s)
        return srt_path, cost_usd

    async def run_step_video(
        self,
        image_paths: list[str],
        audio_path: str,
        srt_path: str,
        job_dir: str,
        script: dict | None = None,
    ) -> str:
        """Step 6: Assemble final video from images + audio + subtitles.

        If the script has >30s total duration, uses segmentation:
        segment_roteiro -> build_segment_videos -> concat_segments.
        Otherwise calls build_reel_video directly.

        Args:
            image_paths: Paths to reel images.
            audio_path: Path to narration audio.
            srt_path: Path to SRT subtitles.
            job_dir: Job working directory.
            script: Optional script dict (needed for segmentation duration check).

        Returns:
            Path to final video file.
        """
        from src.reels_pipeline.config import REELS_SEGMENT_MAX_DURATION
        from src.reels_pipeline.video_builder import build_reel_video

        video_path = os.path.join(job_dir, "final.mp4")

        total_duration = 0.0
        if script and "cenas" in script:
            total_duration = sum(
                c.get("duracao_segundos", 0) for c in script["cenas"]
            )

        if total_duration > REELS_SEGMENT_MAX_DURATION and script:
            from src.reels_pipeline.video_builder import (
                build_segment_videos,
                concat_segments,
                segment_roteiro,
            )

            segments = segment_roteiro(script, REELS_SEGMENT_MAX_DURATION)
            # Map images to segments based on cena imagem_index
            image_paths_by_segment = []
            for seg in segments:
                seg_images = []
                for cena in seg["cenas"]:
                    idx = cena.get("imagem_index", 0)
                    if idx < len(image_paths):
                        seg_images.append(image_paths[idx])
                if not seg_images and image_paths:
                    seg_images = [image_paths[0]]
                image_paths_by_segment.append(seg_images)

            segment_paths = build_segment_videos(
                segments=segments,
                image_paths_by_segment=image_paths_by_segment,
                audio_path=audio_path,
                srt_path=srt_path,
                job_dir=job_dir,
                config_override=self.config,
            )
            concat_segments(segment_paths, video_path)
        else:
            build_reel_video(
                image_paths=image_paths,
                audio_path=audio_path,
                srt_path=srt_path,
                output_path=video_path,
                config_override=self.config,
            )

        return video_path

    async def run_step_video_hailuo(
        self,
        image_paths: list[str],
        audio_path: str,
        srt_path: str,
        job_dir: str,
        script: dict | None = None,
    ) -> str:
        """Step 6 v2: Generate per-scene Hailuo video clips, concatenate with audio + subtitles.

        Per REELV2-03: Uses Kie.ai Hailuo 2.3 Standard for image-to-video per scene.
        Polls all tasks in parallel. Falls back to static image clip on failure.
        Final assembly via FFmpeg xfade + audio + SRT subtitles.

        Args:
            image_paths: Paths to per-scene images (1 per cena).
            audio_path: Path to TTS narration audio.
            srt_path: Path to SRT subtitles.
            job_dir: Job working directory.
            script: Script dict with cenas (for motion prompt context).

        Returns:
            Path to final video file.
        """
        import asyncio as aio
        import subprocess

        from src.video_gen.kie_client import KieSora2Client
        from src.video_gen.gcs_uploader import GCSUploader
        from src.video_gen.video_prompt_builder import VideoPromptBuilder
        from src.reels_pipeline.video_builder import concat_clips_with_audio

        kie = KieSora2Client()
        gcs = GCSUploader()
        builder = VideoPromptBuilder()
        cenas = (script or {}).get("cenas", [])
        clips_dir = os.path.join(job_dir, "clips")
        os.makedirs(clips_dir, exist_ok=True)

        hailuo_model = "hailuo/2-3-image-to-video-standard"
        hailuo_duration = 6

        # Phase 1: Upload images to GCS and build motion prompts
        tasks_info = []
        for i, img_path in enumerate(image_paths):
            cena = cenas[i] if i < len(cenas) else {}
            gcs_key = f"reels/{os.path.basename(job_dir)}/scene_{i}.jpg"
            public_url = gcs.upload_image(img_path, gcs_key)

            motion = builder.build_motion_prompt(
                theme_key="generico",
                phrase_context=cena.get("narracao", ""),
                scene=cena.get("legenda_overlay", ""),
            )
            tasks_info.append({"index": i, "url": public_url, "motion": motion, "img_path": img_path})
            logger.info(f"Scene {i}: uploaded to GCS, motion prompt built")

        # Phase 2: Create all Hailuo tasks
        task_ids = []
        for info in tasks_info:
            try:
                task_id = await kie.create_task(
                    image_url=info["url"],
                    prompt=info["motion"],
                    duration=hailuo_duration,
                    model=hailuo_model,
                )
                task_ids.append({"index": info["index"], "task_id": task_id, "img_path": info["img_path"]})
                logger.info(f"Scene {info['index']}: Hailuo task created: {task_id}")
            except Exception as e:
                logger.error(f"Scene {info['index']}: failed to create Hailuo task: {e}")
                task_ids.append({"index": info["index"], "task_id": None, "img_path": info["img_path"]})

        # Phase 3: Poll all tasks in parallel
        async def poll_and_download(entry):
            idx = entry["index"]
            tid = entry["task_id"]
            img_path = entry["img_path"]
            clip_path = os.path.join(clips_dir, f"clip_{idx:02d}.mp4")

            if tid is None:
                logger.warning(f"Scene {idx}: no task, using static fallback")
                subprocess.run([
                    "ffmpeg", "-y", "-loop", "1", "-t", str(hailuo_duration),
                    "-i", img_path,
                    "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:-1:-1:color=black",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                    clip_path,
                ], capture_output=True, timeout=60)
                return clip_path

            try:
                result = await kie.poll_until_complete(tid)
                if result and result.video_url:
                    await kie.download_video(result.video_url, clip_path)
                    logger.info(f"Scene {idx}: Hailuo clip downloaded")
                    return clip_path
            except Exception as e:
                logger.error(f"Scene {idx}: Hailuo poll/download failed: {e}")

            # Fallback: static image for 6s
            logger.warning(f"Scene {idx}: Hailuo failed, using static fallback")
            subprocess.run([
                "ffmpeg", "-y", "-loop", "1", "-t", str(hailuo_duration),
                "-i", img_path,
                "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:-1:-1:color=black",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                clip_path,
            ], capture_output=True, timeout=60)
            return clip_path

        clip_paths_raw = await aio.gather(*[poll_and_download(e) for e in task_ids])
        clip_paths = [p for p in clip_paths_raw if p and os.path.isfile(p)]

        if not clip_paths:
            raise RuntimeError("No video clips generated (all Hailuo tasks failed)")

        # Phase 4: Concat clips with audio + subtitles
        video_path = os.path.join(job_dir, "final.mp4")
        concat_clips_with_audio(
            clip_paths=clip_paths,
            audio_path=audio_path,
            srt_path=srt_path,
            output_path=video_path,
            transition_duration=0.3,
        )

        logger.info(f"Hailuo reel assembled: {video_path} from {len(clip_paths)} clips")
        return video_path

    # ------------------------------------------------------------------
    # Full pipeline (backward compatible)
    # ------------------------------------------------------------------

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

        # Step 1 - Prompt / setup
        prompt_data = await self.run_step_prompt(tema, character_id)
        job_dir = prompt_data["job_dir"]
        images_dir = prompt_data["images_dir"]

        logger.info(f"Pipeline started: tema='{tema}', job_dir={job_dir}")

        # Step 2 - Images (0-20%)
        image_paths = await self.run_step_images(
            tema, character_id, job_dir, images_dir
        )
        _progress("images", 20)

        # Step 3 - Script (20-40%)
        script = await self.run_step_script(
            image_paths, tema, job_dir, character_id
        )
        cost_usd += 0.001  # Gemini script gen ~$0.001
        _progress("script", 40)

        # Step 4 - TTS (40-60%)
        narration_text = script.get("narracao_completa", "")
        audio_path, tts_cost = await self.run_step_tts(narration_text, job_dir)
        cost_usd += tts_cost
        _progress("tts", 60)

        # Step 5 - Transcription (60-75%)
        srt_path, srt_cost = await self.run_step_srt(audio_path, job_dir)
        cost_usd += srt_cost
        _progress("transcription", 75)

        # Step 6 - Assembly (75-95%)
        video_path = await self.run_step_video(
            image_paths, audio_path, srt_path, job_dir, script
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
