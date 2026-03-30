"""KieSora2Client — async Kie.ai Sora 2 image-to-video API client.

Handles the full lifecycle: create task, poll with exponential backoff,
download video. Supports character_id_list for visual consistency (D-10),
configurable duration (D-08), and async httpx (project convention).

API Reference: https://docs.kie.ai/market/sora2/sora-2-image-to-video
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx

logger = logging.getLogger("clip-flow.kie_client")

# ── Config defaults (overridden by config module when available) ────────

_KIE_API_KEY = os.getenv("KIE_API_KEY", "")
_VIDEO_MODEL = os.getenv("VIDEO_MODEL", "sora-2-image-to-video-stable")
_VIDEO_COST_PER_SECOND = float(os.getenv("VIDEO_COST_PER_SECOND", "0.0175"))
_GENERATED_VIDEOS_DIR = os.getenv("GENERATED_VIDEOS_DIR", "output/videos")
_KIE_POLL_INITIAL_INTERVAL = int(os.getenv("KIE_POLL_INITIAL_INTERVAL", "5"))
_KIE_POLL_MAX_INTERVAL = int(os.getenv("KIE_POLL_MAX_INTERVAL", "30"))
_KIE_POLL_TIMEOUT = int(os.getenv("KIE_POLL_TIMEOUT", "600"))

# ── Transient error retry config (Phase 18) ──────────────────────────────

_MAX_TRANSIENT_RETRIES = 2
_TRANSIENT_RETRY_BASE_SECONDS = 5


def _get_config(attr: str, default):
    """Try to read from config module, fall back to module-level default."""
    try:
        import config as cfg
        return getattr(cfg, attr, default)
    except (ImportError, AttributeError):
        return default


# ── Result dataclass ────────────────────────────────────────────────────


@dataclass
class VideoGenerationResult:
    """Result of a Kie.ai Sora 2 video generation task."""

    video_url: str  # Remote URL from Kie.ai (expires in 24h)
    local_path: str = ""  # Local path after download
    task_id: str = ""  # Kie.ai taskId
    prompt_used: str = ""  # Motion prompt sent to Kie.ai
    model: str = ""  # e.g., "sora-2-image-to-video"
    duration_seconds: int = 10
    cost_usd: float = 0.0  # Estimated cost
    generation_time_ms: int = 0  # costTime from API
    character_ids: list[str] = field(default_factory=list)
    source_image_url: str = ""  # Public URL of the input image


# ── Exceptions ──────────────────────────────────────────────────────────


class KieAPIError(Exception):
    """Error returned by the Kie.ai API."""

    def __init__(self, message: str, code: int = 0):
        self.code = code
        super().__init__(f"[KIE-{code}] {message}")


# ── Client ──────────────────────────────────────────────────────────────


class KieSora2Client:
    """Async client for Kie.ai Sora 2 image-to-video API.

    Usage::

        client = KieSora2Client(api_key="...")
        result = await client.generate_video(
            image_url="https://cdn.example.com/mago.png",
            prompt="Wizard slowly raises staff, golden particles float upward",
        )
        if result:
            print(result.local_path)
    """

    BASE_URL = "https://api.kie.ai/api/v1"

    def __init__(self, api_key: str | None = None):
        """Initialize with API key from param, config module, or env var.

        Raises ValueError if no API key is found.
        """
        self._api_key = (
            api_key
            or _get_config("KIE_API_KEY", None)
            or _KIE_API_KEY
        )
        if not self._api_key:
            raise ValueError(
                "KIE_API_KEY not configured. "
                "Get your key at: https://kie.ai/api-key"
            )

        self._headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        self._timeout = httpx.Timeout(30.0, read=120.0)

    # ── Payload builders per model format ─────────────────────────────

    def _build_payload(
        self,
        input_format: str,
        model: str,
        image_url: str,
        prompt: str,
        duration: int,
        negative_prompt: str = "",
        character_ids: list[str] | None = None,
        aspect_ratio: str = "9:16",
    ) -> dict:
        """Build Kie.ai createTask payload per model format.

        Verified against official docs at docs.kie.ai/market/* (2026-03).

        Key differences per model:
        - Image field: image_url (str) vs image_urls (array) vs input_urls (array)
        - Duration: string for most, INTEGER for seedance 1.5
        - Sora uses n_frames instead of duration
        - Only Kling v2.x supports negative_prompt field
        - Kling 3.0 requires aspect_ratio, multi_shots, sound
        """
        dur = str(duration)

        # ── Hailuo 2.3 Standard/Pro ──────────────────────────────
        # Docs: image_url (singular), duration "6"/"10", resolution "768P"/"1080P"
        # Note: 10s + 1080P is not supported (use 768P for 10s)
        if input_format == "hailuo":
            res = "768P" if duration >= 10 else "1080P"
            return {"model": model, "input": {
                "prompt": prompt,
                "image_url": image_url,
                "duration": dur,
                "resolution": res,
            }}

        # ── Wan 2.6 ─────────────────────────────────────────────
        # Docs: image_urls (array max 1), duration "5"/"10"/"15", resolution "720p"/"1080p"
        if input_format == "wan":
            return {"model": model, "input": {
                "prompt": prompt,
                "image_urls": [image_url],
                "duration": dur,
                "resolution": "1080p",
            }}

        # ── Wan 2.6 Flash ───────────────────────────────────────
        # Docs: image_urls (array max 1), audio (bool, required), duration "5"/"10"/"15"
        if input_format == "wan_flash":
            return {"model": model, "input": {
                "prompt": prompt,
                "image_urls": [image_url],
                "duration": dur,
                "resolution": "1080p",
                "audio": False,
            }}

        # ── Bytedance V1 Pro Fast / V1 Lite ─────────────────────
        # Docs: image_url (singular), duration "5"/"10", resolution "720p"/"1080p"
        if input_format == "bytedance":
            return {"model": model, "input": {
                "prompt": prompt,
                "image_url": image_url,
                "duration": dur,
                "resolution": "720p",
            }}

        # ── Bytedance Seedance 1.5 Pro ──────────────────────────
        # Docs: input_urls (array 0-2), duration INTEGER (4/8/12, NOT string),
        #       aspect_ratio "1:1"/"4:3"/"3:4"/"16:9"/"9:16"/"21:9", resolution "720p"/"1080p"
        if input_format == "seedance":
            sd_dur = min(int(duration), 12)
            sd_ar = aspect_ratio if aspect_ratio in ("1:1", "4:3", "3:4", "16:9", "9:16", "21:9") else "9:16"
            return {"model": model, "input": {
                "prompt": prompt,
                "input_urls": [image_url],
                "aspect_ratio": sd_ar,
                "duration": sd_dur,  # INTEGER, not string
                "resolution": "720p",
            }}

        # ── Kling v2.1 / v2.5 ─���────────────────────────────────
        # Docs: image_url (singular), duration "5"/"10", negative_prompt (max 500),
        #       cfg_scale 0-1 (default 0.5)
        if input_format == "kling_v2":
            return {"model": model, "input": {
                "prompt": prompt,
                "image_url": image_url,
                "duration": dur,
                "negative_prompt": negative_prompt or "text, watermark, blurry, low quality, distorted, human hands",
                "cfg_scale": 0.5,
            }}

        # ── Kling 3.0 ──────────────────────────────────────────
        # Docs: image_urls (array max 2), duration "3"-"15", mode "std"/"pro",
        #       aspect_ratio "16:9"/"9:16"/"1:1" (optional if image provided),
        #       multi_shots (bool, required), sound (bool, required),
        #       multi_prompt (array, required when multi_shots=true)
        if input_format == "kling_v3":
            # Normalize aspect_ratio — Kling only accepts "16:9", "9:16", "1:1"
            ar = aspect_ratio if aspect_ratio in ("16:9", "9:16", "1:1") else "9:16"
            return {"model": model, "input": {
                "prompt": prompt,
                "image_urls": [image_url],
                "duration": dur,
                "mode": "pro",
                "aspect_ratio": ar,
                "sound": False,
                "multi_shots": False,
            }}

        # ── Grok Imagine ────────────────────────────────────────
        # Docs: image_urls (array max 7), mode "normal"/"fun"/"spicy",
        #       duration "6"/"10", resolution "480p"/"720p", aspect_ratio "2:3"/"3:2"/"1:1"/"16:9"/"9:16"
        if input_format == "grok":
            grok_ar = aspect_ratio if aspect_ratio in ("2:3", "3:2", "1:1", "16:9", "9:16") else "9:16"
            return {"model": model, "input": {
                "prompt": prompt,
                "image_urls": [image_url],
                "duration": dur,
                "resolution": "720p",
                "mode": "normal",
                "aspect_ratio": grok_ar,
            }}

        # ── Sora 2 (default) ────────────────────────────────────
        # Docs: image_urls (array max 1), n_frames "10"/"15" (NOT duration),
        #       upload_method "s3"/"oss" (required), aspect_ratio "portrait"/"landscape"
        ar = "portrait" if aspect_ratio in ("9:16", "3:4", "2:3") else "landscape"
        return {"model": model, "input": {
            "prompt": prompt,
            "image_urls": [image_url],
            "aspect_ratio": ar,
            "n_frames": dur,
            "remove_watermark": True,
            "upload_method": "s3",
            "character_id_list": character_ids or [],
        }}

    # ── Task creation ───────────────────────────────────────────────────

    async def create_task(
        self,
        image_url: str,
        prompt: str,
        duration: int = 10,
        character_ids: list[str] | None = None,
        aspect_ratio: str = "portrait",
        model: str | None = None,
        negative_prompt: str = "",
    ) -> str:
        """Submit an image-to-video generation task.

        Args:
            image_url: Publicly accessible image URL (JPEG/PNG/WebP, max 10MB).
            prompt: Motion/animation description (max 10,000 chars).
            duration: Video length in seconds (10 or 15).
            negative_prompt: Things to avoid in the video (only used by models that support it).
            character_ids: Kie.ai character IDs for visual consistency (max 5).
            aspect_ratio: "portrait" (4:5) or "landscape" (16:9).

        Returns:
            taskId string for polling.

        Raises:
            KieAPIError: On API errors (401, 402, 422, 429, 500+).
        """
        resolved_model = model or _get_config("VIDEO_MODEL", _VIDEO_MODEL)

        # Resolve input format and valid durations from config
        input_format = "sora"  # default fallback
        valid_durations = None
        try:
            from config import VIDEO_MODELS
            model_info = VIDEO_MODELS.get(resolved_model, {})
            input_format = model_info.get("input_format", "sora")
            valid_durations = model_info.get("durations")
        except (ImportError, AttributeError):
            # Detect by model prefix
            if resolved_model.startswith("hailuo/"):
                input_format = "hailuo"
            elif resolved_model.startswith("wan/"):
                input_format = "wan"
            elif resolved_model.startswith("bytedance/"):
                input_format = "bytedance"
            elif resolved_model.startswith("kling"):
                input_format = "kling"
            elif resolved_model.startswith("grok"):
                input_format = "grok"
            elif resolved_model.startswith("sora"):
                input_format = "sora"

        # Snap duration to nearest valid value for this model
        if valid_durations:
            duration = min(valid_durations, key=lambda d: abs(d - duration))

        # Build payload per input format.
        # Each format has specific field names and types verified against Kie.ai API.
        # Key differences: image field name (image_url vs image_urls vs input_urls),
        # duration type (string), negative_prompt support, and extra required fields.
        payload = self._build_payload(
            input_format=input_format,
            model=resolved_model,
            image_url=image_url,
            prompt=prompt,
            duration=duration,
            negative_prompt=negative_prompt,
            character_ids=character_ids,
            aspect_ratio=aspect_ratio,
        )

        logger.info(
            "Creating video task: model=%s duration=%ds format=%s",
            resolved_model, duration, input_format,
        )

        # Retry loop for transient errors (429, 5xx, timeouts) -- Phase 18
        last_error = None
        response = None
        for attempt in range(_MAX_TRANSIENT_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    response = await client.post(
                        f"{self.BASE_URL}/jobs/createTask",
                        json=payload,
                        headers=self._headers,
                    )
                # Check for transient HTTP errors
                if response.status_code in (429, 500, 502, 503):
                    wait = _TRANSIENT_RETRY_BASE_SECONDS * (2 ** attempt)
                    logger.warning(
                        "Transient error %d on attempt %d/%d, retrying in %ds",
                        response.status_code, attempt + 1,
                        _MAX_TRANSIENT_RETRIES + 1, wait,
                    )
                    last_error = KieAPIError(
                        f"HTTP {response.status_code}",
                        code=response.status_code,
                    )
                    await asyncio.sleep(wait)
                    continue
                break  # Non-transient response, proceed
            except httpx.TimeoutException as e:
                wait = _TRANSIENT_RETRY_BASE_SECONDS * (2 ** attempt)
                logger.warning(
                    "Timeout on attempt %d/%d, retrying in %ds: %s",
                    attempt + 1, _MAX_TRANSIENT_RETRIES + 1, wait, e,
                )
                last_error = e
                await asyncio.sleep(wait)
                continue
        else:
            # All retries exhausted
            raise last_error or KieAPIError("All retries exhausted", code=0)

        self._handle_http_error(response)

        result = response.json()
        if result.get("code") != 200:
            raise KieAPIError(
                result.get("msg", "Unknown error"),
                code=result.get("code", 0),
            )

        task_id = result["data"]["taskId"]
        logger.info("Sora 2 task created: %s", task_id)
        return task_id

    # ── Status polling ──────────────────────────────────────────────────

    async def get_task_status(self, task_id: str) -> dict:
        """Get current task status and results.

        Returns:
            Dict with keys: state, progress, resultJson, failCode,
            failMsg, costTime, createTime, completeTime.
        """
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self.BASE_URL}/jobs/recordInfo",
                params={"taskId": task_id},
                headers=self._headers,
            )

        self._handle_http_error(response)

        result = response.json()
        if result.get("code") != 200:
            raise KieAPIError(
                result.get("msg", "Unknown error"),
                code=result.get("code", 0),
            )

        return result["data"]

    async def poll_until_complete(
        self,
        task_id: str,
        initial_interval: int | None = None,
        max_interval: int | None = None,
        timeout: int | None = None,
    ) -> VideoGenerationResult | None:
        """Poll task status until success, failure, or timeout.

        Uses exponential backoff: interval *= 1.5, capped at max_interval.

        Args:
            task_id: Kie.ai task ID from create_task().
            initial_interval: Seconds between first polls (default from config).
            max_interval: Max seconds between polls (default from config).
            timeout: Total seconds before giving up (default from config).

        Returns:
            VideoGenerationResult on success, None on failure or timeout.
        """
        interval = float(
            initial_interval
            or _get_config("KIE_POLL_INITIAL_INTERVAL", _KIE_POLL_INITIAL_INTERVAL)
        )
        max_int = float(
            max_interval
            or _get_config("KIE_POLL_MAX_INTERVAL", _KIE_POLL_MAX_INTERVAL)
        )
        total_timeout = float(
            timeout
            or _get_config("KIE_POLL_TIMEOUT", _KIE_POLL_TIMEOUT)
        )

        # States that mean "still processing"
        active_states = {"waiting", "queuing", "generating"}

        start = time.monotonic()
        logger.info(
            "Polling task %s (interval=%.1fs, max=%.1fs, timeout=%.0fs)",
            task_id, interval, max_int, total_timeout,
        )

        while True:
            await asyncio.sleep(interval)

            elapsed = time.monotonic() - start
            if elapsed >= total_timeout:
                logger.error(
                    "Task %s timed out after %.0fs", task_id, elapsed,
                )
                return None

            try:
                data = await self.get_task_status(task_id)
            except Exception as e:
                logger.warning("Poll error for %s: %s", task_id, e)
                interval = min(interval * 1.5, max_int)
                continue

            state = data.get("state", "")
            progress = data.get("progress", 0)

            logger.info(
                "Task %s: state=%s progress=%s%% elapsed=%.0fs",
                task_id, state, progress, elapsed,
            )

            if state == "success":
                return self._parse_success_result(task_id, data)

            if state == "fail":
                fail_code = data.get("failCode", "")
                fail_msg = data.get("failMsg", "Unknown error")
                logger.error(
                    "Task %s failed: [%s] %s", task_id, fail_code, fail_msg,
                )
                return None

            if state not in active_states:
                logger.warning(
                    "Task %s unexpected state: %s", task_id, state,
                )

            # Exponential backoff, capped
            interval = min(interval * 1.5, max_int)

    # ── Video download ──────────────────────────────────────────────────

    async def download_video(self, video_url: str, output_path: str) -> str:
        """Stream-download a video file from Kie.ai CDN.

        Args:
            video_url: Remote video URL (expires in 24h).
            output_path: Local file path to write to.

        Returns:
            The output_path after successful download.
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        logger.info("Downloading video to %s", output_path)

        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, read=300.0)) as client:
            async with client.stream("GET", video_url) as response:
                response.raise_for_status()
                with open(output_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        f.write(chunk)

        file_size = output.stat().st_size
        logger.info(
            "Video downloaded: %s (%.2f MB)",
            output_path, file_size / (1024 * 1024),
        )
        return output_path

    # ── High-level convenience method ───────────────────────────────────

    async def generate_video(
        self,
        image_url: str,
        prompt: str,
        duration: int = 10,
        character_ids: list[str] | None = None,
        output_dir: str | None = None,
        model: str | None = None,
        negative_prompt: str = "",
    ) -> VideoGenerationResult | None:
        """Full pipeline: create task -> poll -> download video.

        Args:
            image_url: Publicly accessible image URL.
            prompt: Motion/animation prompt.
            duration: Video duration in seconds (10 or 15).
            character_ids: Character IDs for visual consistency.
            output_dir: Directory for downloaded video. Defaults to config.

        Returns:
            VideoGenerationResult with local_path set, or None on failure.
        """
        # Create task
        try:
            task_id = await self.create_task(
                image_url=image_url,
                prompt=prompt,
                duration=duration,
                character_ids=character_ids,
                model=model,
                negative_prompt=negative_prompt,
            )
        except (KieAPIError, httpx.HTTPError) as e:
            logger.error("Failed to create video task: %s", e)
            return None

        # Poll until complete
        result = await self.poll_until_complete(task_id)
        if result is None:
            return None

        # Calculate cost
        cost_per_second = _get_config("VIDEO_COST_PER_SECOND", _VIDEO_COST_PER_SECOND)
        result.cost_usd = duration * cost_per_second
        result.prompt_used = prompt
        result.source_image_url = image_url
        result.character_ids = character_ids or []
        result.duration_seconds = duration

        # Download video
        videos_dir = output_dir or str(
            _get_config("GENERATED_VIDEOS_DIR", _GENERATED_VIDEOS_DIR)
        )
        output_path = str(Path(videos_dir) / f"{task_id}.mp4")

        try:
            result.local_path = await self.download_video(
                result.video_url, output_path,
            )
        except (httpx.HTTPError, OSError) as e:
            logger.error(
                "Failed to download video %s: %s", task_id, e,
            )
            # Result still valid — video_url is available for manual download
            logger.warning(
                "Video URL still available (expires 24h): %s", result.video_url,
            )

        return result

    # ── Internal helpers ────────────────────────────────────────────────

    def _handle_http_error(self, response: httpx.Response) -> None:
        """Raise descriptive KieAPIError for HTTP-level errors."""
        if response.is_success:
            return

        code = response.status_code
        error_map = {
            401: "Unauthorized — check KIE_API_KEY",
            402: "Insufficient credits — top up at kie.ai",
            404: "Task not found — verify taskId",
            422: "Validation error — check request parameters",
            429: "Rate limited — back off and retry",
            455: "Service unavailable — retry later",
            500: "Server error — retry with backoff",
            501: "Generation failed — try a different prompt",
            505: "Feature disabled — contact Kie.ai support",
        }
        msg = error_map.get(code, f"HTTP {code}: {response.text[:200]}")
        raise KieAPIError(msg, code=code)

    def _parse_success_result(
        self, task_id: str, data: dict,
    ) -> VideoGenerationResult:
        """Parse a successful task response into VideoGenerationResult."""
        # resultJson is a JSON STRING that must be parsed
        result_json_str = data.get("resultJson", "{}")
        result_parsed = json.loads(result_json_str)
        result_urls = result_parsed.get("resultUrls", [])

        if not result_urls:
            logger.error("Task %s succeeded but no resultUrls found", task_id)
            # Return result with empty URL — caller can check
            video_url = ""
        else:
            video_url = result_urls[0]
            logger.info("Video ready: %s", video_url)

        cost_time = data.get("costTime", 0)
        model = data.get("model", _get_config("VIDEO_MODEL", _VIDEO_MODEL))

        return VideoGenerationResult(
            video_url=video_url,
            task_id=task_id,
            model=model,
            generation_time_ms=cost_time,
        )
