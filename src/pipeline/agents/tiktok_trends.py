"""TikTok Trends Agent — stub para TikTok Creative Center.

Requer TIKTOK_API_KEY no .env para funcionar.
Quando implementado, buscara trends virais do TikTok Brasil.
"""

import os
import logging

from src.pipeline.agents.async_base import AsyncSourceAgent
from src.pipeline.models_v2 import TrendEvent, TrendSource

logger = logging.getLogger("clip-flow.agent.tiktok")


class TikTokTrendsAgent(AsyncSourceAgent):
    """TikTok Creative Center trends (stub)."""

    def __init__(self):
        super().__init__("tiktok_trends")

    async def fetch(self) -> list[TrendEvent]:
        """Stub — retorna lista vazia ate implementacao."""
        self.logger.debug("TikTok agent e um stub — retornando lista vazia")
        return []

    async def is_available(self) -> bool:
        """Disponivel quando TIKTOK_API_KEY estiver configurada."""
        return bool(os.getenv("TIKTOK_API_KEY"))
