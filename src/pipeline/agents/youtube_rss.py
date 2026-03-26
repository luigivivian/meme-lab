"""YouTube RSS Agent — ultimos videos de canais BR virais via feed RSS publico.

O endpoint chart=mostpopular foi desativado pelo YouTube. Usamos RSS por channel_id,
que retorna os 15 videos mais recentes de cada canal — sem API key.

Canais monitorados (verificados e funcionais):
  - Porta dos Fundos   — esquetes de comedia, sempre viral
  - Manual do Mundo    — ciencia popular + humor, muito compartilhado
  - KondZilla          — maior canal de funk BR, indicador de trends musicais
  - BRKsEDU            — gaming/entretenimento, grande audiencia jovem BR
  - UmDois Podcast     — podcast cannabis/cultura BR, alto engajamento
  - Hempadao TV        — conteudo cannabis medicinal/educativo BR
  - Torrando Tomazine  — cultura cannabis/entrevistas BR

Score baseado no tipo de canal:
  - Comedia/Humor: 0.75 (alto potencial de meme)
  - Cannabis/Cultura 420: 0.70 (relevancia direta pro Mago Mestre)
  - Viral/Entretenimento: 0.65
  - Posicao no feed ajusta +0.0 (primeiro) ate -0.15 (ultimo)
"""

import asyncio
import logging
import time

import feedparser

from config import YOUTUBE_RSS_MAX_PER_CATEGORY
from src.pipeline.agents.async_base import AsyncSourceAgent
from src.pipeline.models_v2 import TrendEvent, TrendSource

logger = logging.getLogger("clip-flow.agent.youtube_rss")

# (channel_id, nome, score_base, categoria)
_CHANNELS = [
    # Comedia/Humor
    ("UCEWHPFNilsT0IfQfutVzsag", "Porta dos Fundos", 0.75, "comedia"),
    ("UCKHhA5hN2UohhFDfNXB_cvQ", "Manual do Mundo",  0.68, "entretenimento"),
    # Musica/Cultura
    ("UCffDXn7ycAzwL2LDlbyWOTw", "KondZilla",         0.65, "musica_viral"),
    ("UCWKtHaeXVzUscYGcm0hEunw", "BRKsEDU",           0.60, "gaming"),
    # Cannabis/Cultura 420
    ("UCoj1MMpCJg1PZzH5cr3pr7g", "UmDois Podcast",    0.70, "cannabis_cultura"),
    ("UCcuBfWaT2n7WFfO-x140Xmg", "Hempadao TV",       0.70, "cannabis_medicinal"),
    ("UCqWRJJWjyw8zn3D4Cz2o7Xg", "Torrando Tomazine",  0.68, "cannabis_cultura"),
]

_RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


class YouTubeRSSAgent(AsyncSourceAgent):
    """Busca videos recentes de canais brasileiros virais via RSS publico."""

    def __init__(self, max_per_channel: int = YOUTUBE_RSS_MAX_PER_CATEGORY):
        super().__init__("youtube_rss")
        self.max_per_channel = max_per_channel

    async def fetch(self) -> list[TrendEvent]:
        try:
            events = await asyncio.to_thread(self._fetch_all_channels)
            self.logger.info(f"YouTube RSS: {len(events)} eventos coletados")
            return events
        except Exception as e:
            self.logger.error(f"YouTube RSS falhou: {e}")
            return []

    def _fetch_all_channels(self) -> list[TrendEvent]:
        seen: set[str] = set()
        events: list[TrendEvent] = []

        for channel_id, channel_name, base_score, category in _CHANNELS:
            url = _RSS_URL.format(channel_id=channel_id)
            try:
                feed = feedparser.parse(url)
                entries = feed.entries[: self.max_per_channel]
                for i, entry in enumerate(entries):
                    title: str = entry.get("title", "").strip()
                    if not title or len(title) < 5:
                        continue
                    title_lower = title.lower()
                    if title_lower in seen:
                        continue
                    seen.add(title_lower)

                    # Penalidade progressiva por posicao no feed
                    position_penalty = min(0.15, i * 0.01)
                    score = round(base_score - position_penalty, 2)

                    events.append(
                        TrendEvent(
                            title=title,
                            source=TrendSource.YOUTUBE,
                            score=score,
                            category=category,
                            url=entry.get("link"),
                            metadata={
                                "youtube_channel": channel_name,
                                "position": i + 1,
                            },
                        )
                    )
                time.sleep(0.2)
            except Exception as e:
                self.logger.warning(f"Falha ao buscar canal '{channel_name}': {e}")

        return events

    async def is_available(self) -> bool:
        try:
            import feedparser  # noqa: F401
            return True
        except ImportError:
            return False
