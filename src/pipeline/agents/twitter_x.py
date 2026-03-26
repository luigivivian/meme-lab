"""Twitter/X Agent — stub para Twitter API v2.

Requer TWITTER_BEARER_TOKEN no .env para funcionar.
Quando implementado, buscara trending topics do Brasil.
"""

import os
import logging

from src.pipeline.agents.async_base import AsyncSourceAgent
from src.pipeline.models_v2 import TrendEvent, TrendSource

logger = logging.getLogger("clip-flow.agent.twitter_x")


class TwitterXAgent(AsyncSourceAgent):
    """Twitter/X API v2 trending topics (stub)."""

    def __init__(self):
        super().__init__("twitter_x")

    async def fetch(self) -> list[TrendEvent]:
        """Stub — retorna lista vazia ate implementacao."""
        self.logger.debug("Twitter/X agent e um stub — retornando lista vazia")
        return []

    async def is_available(self) -> bool:
        """Disponivel quando TWITTER_BEARER_TOKEN estiver configurada."""
        return bool(os.getenv("TWITTER_BEARER_TOKEN"))
