"""YouTube Shorts Agent — stub para YouTube Data API v3.

Requer YOUTUBE_API_KEY no .env para funcionar.
Quando implementado, buscara shorts trending no Brasil.
"""

import os
import logging

from src.pipeline.agents.async_base import AsyncSourceAgent
from src.pipeline.models_v2 import TrendEvent, TrendSource

logger = logging.getLogger("clip-flow.agent.youtube")


class YouTubeShortsAgent(AsyncSourceAgent):
    """YouTube Data API v3 shorts trending (stub)."""

    def __init__(self):
        super().__init__("youtube_shorts")

    async def fetch(self) -> list[TrendEvent]:
        """Stub — retorna lista vazia ate implementacao."""
        self.logger.debug("YouTube agent e um stub — retornando lista vazia")
        return []

    async def is_available(self) -> bool:
        """Disponivel quando YOUTUBE_API_KEY estiver configurada."""
        return bool(os.getenv("YOUTUBE_API_KEY"))
