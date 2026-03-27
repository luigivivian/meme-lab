"""Instagram Explore Agent — stub para Instagram Graph API.

Requer INSTAGRAM_ACCESS_TOKEN no .env para funcionar.
Quando implementado, buscara hashtags trending no Instagram.
"""

import os
import logging

from src.pipeline.agents.async_base import AsyncSourceAgent
from src.pipeline.models_v2 import TrendEvent, TrendSource

logger = logging.getLogger("clip-flow.agent.instagram")


class InstagramExploreAgent(AsyncSourceAgent):
    """Instagram Graph API hashtags trending (stub)."""

    def __init__(self):
        super().__init__("instagram_explore")

    async def fetch(self) -> list[TrendEvent]:
        """Stub — retorna lista vazia ate implementacao."""
        self.logger.debug("Instagram agent e um stub — retornando lista vazia")
        return []

    async def is_available(self) -> bool:
        """Disponivel quando INSTAGRAM_ACCESS_TOKEN estiver configurada."""
        return bool(os.getenv("INSTAGRAM_ACCESS_TOKEN"))
