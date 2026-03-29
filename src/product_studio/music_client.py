"""Kie.ai Suno API client for background music generation. Per D-11, D-12."""

import asyncio
import logging
import os

import httpx
from pathlib import Path

logger = logging.getLogger("clip-flow.ads.music")


class KieMusicClient:
    """Async client for Kie.ai Suno music generation.

    Usage::

        client = KieMusicClient()
        path = await client.generate_and_download(
            style_prompt="cinematic ambient piano, luxury, elegant",
            output_path="output/ads/music.mp3",
        )
    """

    BASE_URL = "https://api.kie.ai/api/v1"

    def __init__(self, api_key: str | None = None):
        self._api_key = api_key or os.getenv("KIE_API_KEY", "")
        self._headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def create_music_task(self, style_prompt: str, title: str = "Product Ad BGM") -> str:
        """Create a Suno music generation task. Returns taskId."""
        payload = {
            "prompt": f"Background music for a product commercial. {style_prompt}",
            "customMode": True,
            "instrumental": True,
            "model": "V4",
            "style": style_prompt,
            "title": title,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.BASE_URL}/generate",
                json=payload,
                headers=self._headers,
            )
            resp.raise_for_status()
            data = resp.json()
            task_id = data["data"]["taskId"]
            logger.info("Suno music task created: %s", task_id)
            return task_id

    async def poll_music_status(self, task_id: str, max_attempts: int = 60, interval: float = 5.0) -> dict:
        """Poll until music generation completes. Returns record with audio_url."""
        for attempt in range(max_attempts):
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/generate/record-info",
                    params={"taskId": task_id},
                    headers=self._headers,
                )
                resp.raise_for_status()
                data = resp.json()["data"]

            status = data.get("status", "")
            if status == "SUCCESS" or data.get("audio_url"):
                logger.info("Suno music ready: %s", task_id)
                return data
            if status in ("FAILED", "ERROR"):
                raise RuntimeError(f"Suno music failed: {data}")

            await asyncio.sleep(interval)

        raise TimeoutError(f"Suno music timed out after {max_attempts} attempts")

    async def download_music(self, audio_url: str, output_path: str) -> str:
        """Download generated music file."""
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.get(audio_url)
            resp.raise_for_status()
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(resp.content)
            logger.info("Music downloaded: %s", output_path)
            return output_path

    async def generate_and_download(self, style_prompt: str, output_path: str) -> str:
        """Full flow: create task -> poll -> download. Returns local file path."""
        task_id = await self.create_music_task(style_prompt)
        result = await self.poll_music_status(task_id)
        audio_url = result.get("audio_url") or result.get("audioUrl", "")
        if not audio_url:
            raise RuntimeError(f"No audio URL in Suno result: {result}")
        return await self.download_music(audio_url, output_path)
