"""Product Ad Pipeline -- 8-step orchestrator for AI video ad generation.

Steps (per D-21):
1. analysis  -- Gemini Vision analyzes product, suggests defaults
2. scene     -- rembg bg removal + Gemini scene composition
3. prompt    -- LLM generates cinematic video prompt
4. video     -- Kie.ai video generation (Wan 2.6 / Kling / Hailuo)
5. copy      -- LLM generates headline + CTA + hashtags
6. audio     -- Suno music + optional TTS narration
7. assembly  -- FFmpeg text overlay + audio mix + subtitles
8. export    -- Multi-format crop/pad with blur background

Per D-20: Same approve/regenerate pattern as ReelsPipeline.
Per D-22: Export is auto-complete (no approval needed).
"""

import asyncio
import logging
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from src.product_studio.config import (
    ADS_OUTPUT_DIR,
    ADS_USD_TO_BRL,
    MUSIC_MAP,
    STYLE_AUDIO_DEFAULTS,
    STYLE_DURATION,
    STYLE_SCENE_COUNT,
    STYLE_VIDEO_MODEL,
)

logger = logging.getLogger("clip-flow.ads.pipeline")


class ProductAdPipeline:
    """8-step orchestrator for product ad video generation.

    Supports per-step execution for interactive stepper mode.
    Each step takes explicit I/O and returns artifacts (no hidden class state).

    Usage::

        pipeline = ProductAdPipeline()
        analysis = await pipeline.run_step_analysis("photo.jpg")
        scene = await pipeline.run_step_scene("photo.jpg", "modern desk", job_dir)
    """

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    def _make_job_dir(self, label: str = "ad") -> str:
        """Create and return a job directory."""
        slug = re.sub(r"[^a-z0-9]+", "_", label.lower().strip())[:30]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        job_dir = os.path.join(ADS_OUTPUT_DIR, f"{timestamp}_{slug}")
        os.makedirs(job_dir, exist_ok=True)
        return job_dir

    # ------------------------------------------------------------------
    # Step 1: Analysis
    # ------------------------------------------------------------------

    async def run_step_analysis(self, product_image_path: str) -> dict:
        """Step 1: Gemini Vision analyzes product, suggests defaults.

        Args:
            product_image_path: Path to product photo.

        Returns:
            Dict with niche, tone, audience, scene_suggestions, product_description.
        """
        from src.product_studio.scene_composer import analyze_product

        result = await analyze_product(product_image_path)
        logger.info("Step analysis complete: niche=%s, tone=%s", result.get("niche"), result.get("tone"))
        return result

    # ------------------------------------------------------------------
    # Step 2: Scene
    # ------------------------------------------------------------------

    async def run_step_scene(
        self, product_image_path: str, scene_prompt: str, job_dir: str,
        scene_mode: str = "compose",
    ) -> str:
        """Step 2: Scene preparation.

        Modes:
            "raw"     — Use original image as-is (no processing)
            "cutout"  — Remove background only (transparent PNG saved as JPG on white)
            "compose" — Remove bg + Gemini scene composition (default)

        Returns:
            Path to scene image.
        """
        from src.product_studio.bg_remover import remove_background

        cutout_path = os.path.join(job_dir, "cutout.png")
        scene_path = os.path.join(job_dir, "scene.jpg")

        if scene_mode == "raw":
            # Just copy original image
            import shutil
            shutil.copy2(product_image_path, scene_path)
            logger.info("Step scene complete (raw): %s", scene_path)
            return scene_path

        # Remove background
        await asyncio.to_thread(remove_background, product_image_path, cutout_path)

        if scene_mode == "cutout":
            # Place cutout on white background
            from PIL import Image as PILImage
            cutout = PILImage.open(cutout_path)
            bg = PILImage.new("RGB", (1080, 1920), (255, 255, 255))
            # Center product in lower 2/3
            cw, ch = cutout.size
            scale = min(900 / cw, 1200 / ch)
            new_size = (int(cw * scale), int(ch * scale))
            cutout_resized = cutout.resize(new_size, PILImage.LANCZOS)
            x = (1080 - new_size[0]) // 2
            y = 500 + (1200 - new_size[1]) // 2
            bg.paste(cutout_resized, (x, y), cutout_resized if cutout_resized.mode == "RGBA" else None)
            bg.save(scene_path, "JPEG", quality=95)
            logger.info("Step scene complete (cutout on white): %s", scene_path)
            return scene_path

        # Compose mode — Gemini scene generation
        from src.product_studio.scene_composer import compose_scene
        await compose_scene(cutout_path, scene_prompt, scene_path)
        logger.info("Step scene complete (composed): %s", scene_path)
        return scene_path

    # ------------------------------------------------------------------
    # Step 3: Prompt
    # ------------------------------------------------------------------

    async def run_step_prompt(
        self,
        product_description: str,
        scene_description: str,
        style: str,
        video_model: str,
        tone: str,
    ) -> str:
        """Step 3: LLM generates cinematic video prompt.

        Args:
            product_description: Product description text.
            scene_description: Scene context description.
            style: Video style (cinematic/narrated/lifestyle).
            video_model: Target video model ID.
            tone: Advertising tone.

        Returns:
            Generated prompt string ready for video generation.
        """
        from src.product_studio.prompt_builder import build_video_prompt

        prompt = await build_video_prompt(
            product_description=product_description,
            scene_description=scene_description,
            style=style,
            video_model=video_model,
            tone=tone,
        )
        logger.info("Step prompt complete: %d chars", len(prompt))
        return prompt

    # ------------------------------------------------------------------
    # Step 4: Video
    # ------------------------------------------------------------------

    async def run_step_video(
        self,
        scene_image_path: str,
        prompt: str,
        video_model: str,
        job_dir: str,
        style: str,
    ) -> str | list[str]:
        """Step 4: Kie.ai video generation.

        Per D-09: single-shot for cinematic (1 clip), multi-scene for narrated/lifestyle.
        Uploads scene image to GCS for public URL before sending to Kie.ai.

        Args:
            scene_image_path: Path to composed scene image.
            prompt: Video motion prompt.
            video_model: Kie.ai model ID.
            job_dir: Job working directory.
            style: Video style for scene count.

        Returns:
            Single video path (cinematic) or list of video paths (narrated/lifestyle).
        """
        from src.video_gen.gcs_uploader import GCSUploader
        from src.video_gen.kie_client import KieSora2Client
        from src.product_studio.prompt_builder import get_negative_prompt

        uploader = GCSUploader()
        client = KieSora2Client()
        scene_count = STYLE_SCENE_COUNT.get(style, 1)
        duration_range = STYLE_DURATION.get(style, (10, 15))
        duration = duration_range[0]
        neg_prompt = get_negative_prompt(style)

        if scene_count <= 1:
            # Single-shot: one clip with fallback models
            import uuid as _uuid
            gcs_name = f"video-inputs/{_uuid.uuid4().hex[:12]}_{Path(scene_image_path).name}"
            public_url = uploader.upload_image(scene_image_path, remote_name=gcs_name)

            # Single attempt — no automatic fallback (each attempt costs credits)
            result = await client.generate_video(
                image_url=public_url,
                prompt=prompt,
                duration=duration,
                output_dir=job_dir,
                model=video_model,
                negative_prompt=neg_prompt,
            )
            if not result or not result.local_path:
                raise RuntimeError(f"Video generation failed with model {video_model} — no result returned")
            logger.info("Step video complete (model=%s): %s", video_model, result.local_path)
            return result.local_path

        # Multi-scene: generate N clips with varying prompts
        gcs_name_multi = f"video-inputs/{_uuid.uuid4().hex[:12]}_{Path(scene_image_path).name}"
        public_url = uploader.upload_image(scene_image_path, remote_name=gcs_name_multi)
        video_paths = []
        for i in range(scene_count):
            scene_prompt = f"Scene {i + 1}/{scene_count}: {prompt}"
            result = await client.generate_video(
                image_url=public_url,
                prompt=scene_prompt,
                duration=duration,
                output_dir=job_dir,
                model=video_model,
                negative_prompt=neg_prompt,
            )
            if result and result.local_path:
                video_paths.append(result.local_path)
            else:
                logger.warning("Scene %d/%d failed, skipping", i + 1, scene_count)

        if not video_paths:
            raise RuntimeError("All video scenes failed")
        logger.info("Step video complete (multi-scene): %d clips", len(video_paths))
        return video_paths

    # ------------------------------------------------------------------
    # Step 5: Copy
    # ------------------------------------------------------------------

    async def run_step_copy(
        self,
        product_name: str,
        product_description: str,
        niche: str,
        tone: str,
        audience: str,
        style: str,
    ) -> dict:
        """Step 5: LLM generates headline + CTA + hashtags.

        Args:
            product_name: Product name.
            product_description: Product description.
            niche: Product niche/category.
            tone: Advertising tone.
            audience: Target audience description.
            style: Video style.

        Returns:
            Dict with headline, cta, hashtags keys.
        """
        from src.product_studio.copy_generator import generate_copy

        result = await generate_copy(
            product_name=product_name,
            product_description=product_description,
            niche=niche,
            tone=tone,
            audience=audience,
            style=style,
        )
        logger.info("Step copy complete: headline='%s'", result.get("headline", ""))
        return result

    # ------------------------------------------------------------------
    # Step 6: Audio
    # ------------------------------------------------------------------

    async def run_step_audio(
        self,
        tone: str,
        audio_mode: str,
        job_dir: str,
        narration_text: str | None = None,
        video_duration: float = 15.0,
    ) -> dict:
        """Step 6: Suno music generation + optional TTS narration.

        Per D-14: Handles mute, music, narrated, ambient audio modes.
        Per D-11: Music genre mapped from tone via MUSIC_MAP.

        Args:
            tone: Ad tone for music genre mapping.
            audio_mode: One of mute/music/narrated/ambient.
            job_dir: Job working directory.
            narration_text: Text for TTS (required if audio_mode == "narrated").
            video_duration: Video duration in seconds for audio trimming.

        Returns:
            Dict with music_path, tts_path, mixed_path keys.
        """
        result = {"music_path": None, "tts_path": None, "mixed_path": None}

        if audio_mode == "mute":
            logger.info("Step audio: mute mode, skipping")
            return result

        # Generate music via Suno
        from src.product_studio.music_client import KieMusicClient

        style_prompt = MUSIC_MAP.get(tone, MUSIC_MAP["profissional"])
        music_client = KieMusicClient()
        music_path = os.path.join(job_dir, "music.mp3")
        await music_client.generate_and_download(style_prompt, music_path)
        result["music_path"] = music_path

        # Generate TTS if narrated mode
        tts_path = None
        if audio_mode == "narrated" and narration_text:
            from src.reels_pipeline.tts import generate_narration

            tts_path = os.path.join(job_dir, "tts.wav")
            await generate_narration(text=narration_text, output_path=tts_path)
            result["tts_path"] = tts_path

        # Mix audio
        from src.product_studio.format_exporter import mix_audio

        mixed_path = os.path.join(job_dir, "mixed_audio.aac")
        mixed = mix_audio(
            tts_path=tts_path,
            music_path=music_path,
            output_path=mixed_path,
            video_duration=video_duration,
            audio_mode=audio_mode,
        )
        result["mixed_path"] = mixed
        logger.info("Step audio complete: mode=%s, mixed=%s", audio_mode, mixed)
        return result

    # ------------------------------------------------------------------
    # Step 7: Assembly
    # ------------------------------------------------------------------

    async def run_step_assembly(
        self,
        video_path: str,
        headline: str | None,
        cta: str | None,
        audio_path: str | None,
        style: str,
        job_dir: str,
        srt_path: str | None = None,
    ) -> str:
        """Step 7: FFmpeg text overlay + audio mix + subtitles.

        Per D-16: overlay_text for headline/CTA.
        Attaches audio and burns subtitles if provided.

        Args:
            video_path: Source video path.
            headline: Headline text (None to skip).
            cta: CTA text (None to skip).
            audio_path: Mixed audio path (None for mute).
            style: Style key for text layout.
            job_dir: Job working directory.
            srt_path: SRT subtitles path (None to skip).

        Returns:
            Path to assembled video.
        """
        from src.product_studio.format_exporter import overlay_text

        assembled_path = os.path.join(job_dir, "assembled.mp4")

        # Text overlay
        if headline or cta:
            overlay_out = os.path.join(job_dir, "overlaid.mp4")
            overlay_text(video_path, overlay_out, headline, cta, style)
            current = overlay_out
        else:
            current = video_path

        # Attach audio if available
        if audio_path:
            audio_out = os.path.join(job_dir, "with_audio.mp4")
            cmd = [
                "ffmpeg", "-y",
                "-i", current,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                "-map", "0:v:0", "-map", "1:a:0",
                "-shortest",
                "-movflags", "+faststart",
                audio_out,
            ]
            await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True, timeout=120, check=True
            )
            current = audio_out

        # Burn subtitles if narrated mode with SRT
        if srt_path and os.path.exists(srt_path):
            srt_out = os.path.join(job_dir, "subtitled.mp4")
            cmd = [
                "ffmpeg", "-y",
                "-i", current,
                "-vf", f"subtitles={srt_path}:force_style='FontSize=20,PrimaryColour=&HFFFFFF&,Outline=2'",
                "-c:v", "libx264", "-crf", "18",
                "-c:a", "copy",
                "-movflags", "+faststart",
                srt_out,
            ]
            await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, text=True, timeout=120, check=True
            )
            current = srt_out

        # Final rename to assembled.mp4
        if current != assembled_path:
            Path(assembled_path).parent.mkdir(parents=True, exist_ok=True)
            os.replace(current, assembled_path)

        logger.info("Step assembly complete: %s", assembled_path)
        return assembled_path

    # ------------------------------------------------------------------
    # Step 8: Export
    # ------------------------------------------------------------------

    async def run_step_export(
        self,
        assembled_path: str,
        job_dir: str,
        formats: list[str] | None = None,
    ) -> dict:
        """Step 8: Multi-format crop/pad with blur background.

        Per D-18, D-22: auto-complete, no approval needed.

        Args:
            assembled_path: Path to assembled master video (9:16).
            job_dir: Job working directory.
            formats: List of format strings (default: ADS_EXPORT_FORMATS).

        Returns:
            Dict mapping format string to output file path.
        """
        from src.product_studio.format_exporter import export_all_formats

        export_dir = os.path.join(job_dir, "exports")
        result = export_all_formats(assembled_path, export_dir, formats)
        logger.info("Step export complete: %d formats", len(result))
        return result

    # ------------------------------------------------------------------
    # Cost estimation
    # ------------------------------------------------------------------

    def estimate_cost(
        self,
        style: str,
        audio_mode: str,
        formats: list[str] | None = None,
    ) -> dict:
        """Estimate total cost in BRL before generation. Per D-19.

        Costs based on design doc estimates:
        - Video: Kie.ai ~$0.175/10s clip (varies by scene count)
        - Audio: Suno ~$0.10/track (free tier if available)
        - Image: Gemini scene composition ~R$0.50
        - Analysis: Gemini Vision ~R$0.05

        Args:
            style: Video style (cinematic/narrated/lifestyle).
            audio_mode: Audio mode (mute/music/narrated/ambient).
            formats: Export formats (cost is zero for FFmpeg-based export).

        Returns:
            Dict with video_brl, audio_brl, image_brl, total_brl.
        """
        scene_count = STYLE_SCENE_COUNT.get(style, 1)
        duration_range = STYLE_DURATION.get(style, (10, 15))
        duration = duration_range[0]

        # Video cost: $0.0175/s per clip
        video_cost_usd = scene_count * duration * 0.0175
        video_brl = video_cost_usd * ADS_USD_TO_BRL

        # Audio cost: Suno ~$0.10/track, TTS ~$0.002 if narrated
        audio_cost_usd = 0.0
        if audio_mode != "mute":
            audio_cost_usd += 0.10  # Suno music
        if audio_mode == "narrated":
            audio_cost_usd += 0.002  # TTS
        audio_brl = audio_cost_usd * ADS_USD_TO_BRL

        # Image cost: scene composition + analysis (Gemini)
        image_brl = 0.50 + 0.05  # R$0.50 scene + R$0.05 analysis

        total_brl = video_brl + audio_brl + image_brl

        return {
            "video_brl": round(video_brl, 2),
            "audio_brl": round(audio_brl, 2),
            "image_brl": round(image_brl, 2),
            "total_brl": round(total_brl, 2),
        }
