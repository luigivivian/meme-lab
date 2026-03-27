"""Facebook Viral Agent — stub para Meta/CrowdTangle API.

Requer FACEBOOK_ACCESS_TOKEN no .env para funcionar.
Quando implementado, buscara posts virais no Facebook.
"""

import os
import logging

from src.pipeline.agents.async_base import AsyncSourceAgent
from src.pipeline.models_v2 import TrendEvent, TrendSource

logger = logging.getLogger("clip-flow.agent.facebook")


class FacebookViralAgent(AsyncSourceAgent):
    """Facebook/Meta posts virais (stub)."""

    def __init__(self):
        super().__init__("facebook_viral")

    async def fetch(self) -> list[TrendEvent]:
        """Stub — retorna lista vazia ate implementacao."""
        self.logger.debug("Facebook agent e um stub — retornando lista vazia")
        return []

    async def is_available(self) -> bool:
        """Disponivel quando FACEBOOK_ACCESS_TOKEN estiver configurada."""
        return bool(os.getenv("FACEBOOK_ACCESS_TOKEN"))
