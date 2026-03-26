"""Brazil Viral RSS Agent — feeds RSS curados de memes e humor brasileiro.

Monitora subreddits de memes BR + portais de cultura pop/viral nacionais.
Sem necessidade de API key — apenas feedparser.

Subreddits meme BR (community-validated, score 0.65):
  - r/HUEstation       — memes brasileiros classicos
  - r/BrasilSimulator  — situacoes absurdas do Brasil
  - r/chinesinhagem    — chineladas da internet BR
  - r/desabafos        — situacoes cotidianas relatable
  - r/eu_nvr           — "eu nunca" memes

Portais BR de viral/pop culture (score 0.60):
  - Hypeness           — cultura pop, trends virais
  - Metropoles         — entretenimento BR
  - Catraca Livre      — viral, cultura
  - Omelete            — pop culture, geek humor
"""

import asyncio
import logging
import time

import feedparser

from config import BRAZIL_VIRAL_RSS_MAX_PER_FEED
from src.pipeline.agents.async_base import AsyncSourceAgent
from src.pipeline.models_v2 import TrendEvent, TrendSource

logger = logging.getLogger("clip-flow.agent.brazil_viral_rss")

# (url, label, score_base)
_REDDIT_FEEDS = [
    ("https://www.reddit.com/r/HUEstation/hot/.rss",      "HUEstation",      0.65),
    ("https://www.reddit.com/r/BrasilSimulator/hot/.rss", "BrasilSimulator", 0.65),
    ("https://www.reddit.com/r/chinesinhagem/hot/.rss",   "chinesinhagem",   0.65),
    ("https://www.reddit.com/r/desabafos/hot/.rss",       "desabafos",       0.60),
    ("https://www.reddit.com/r/eu_nvr/hot/.rss",          "eu_nvr",          0.62),
]

_PORTAL_FEEDS = [
    ("https://www.hypeness.com.br/feed/",        "Hypeness",    0.60),
    ("https://metrop%C3%B3les.com/feed/",        "Metropoles",  0.58),
    ("https://catracalivre.com.br/feed/",        "CatraCalLivre", 0.57),
    ("https://www.omelete.com.br/rss/tudo",      "Omelete",     0.57),
]

# URL alternativa de Metropoles (sem encode)
_METROPOLES_URL = "https://metropoles.com/feed/"


class BrazilViralRSSAgent(AsyncSourceAgent):
    """Feeds RSS curados de memes e viral BR."""

    def __init__(self, max_per_feed: int = BRAZIL_VIRAL_RSS_MAX_PER_FEED):
        super().__init__("brazil_viral_rss")
        self.max_per_feed = max_per_feed

    async def fetch(self) -> list[TrendEvent]:
        try:
            events = await asyncio.to_thread(self._fetch_all)
            self.logger.info(f"Brazil Viral RSS: {len(events)} eventos coletados")
            return events
        except Exception as e:
            self.logger.error(f"Brazil Viral RSS falhou: {e}")
            return []

    def _fetch_all(self) -> list[TrendEvent]:
        seen: set[str] = set()
        events: list[TrendEvent] = []

        all_feeds = list(_REDDIT_FEEDS)
        # Substitui URL codificada do Metropoles pela versao limpa
        portals = [
            (_METROPOLES_URL if label == "Metropoles" else url, label, score)
            for url, label, score in _PORTAL_FEEDS
        ]
        all_feeds.extend(portals)

        for url, label, score_base in all_feeds:
            try:
                feed = feedparser.parse(url)
                entries = feed.entries[: self.max_per_feed]
                for entry in entries:
                    title: str = entry.get("title", "").strip()
                    if not title or len(title) < 5:
                        continue
                    title_lower = title.lower()
                    if title_lower in seen:
                        continue
                    seen.add(title_lower)

                    events.append(
                        TrendEvent(
                            title=title,
                            source=TrendSource.BRAZIL_VIRAL,
                            score=score_base,
                            category="humor",
                            url=entry.get("link"),
                            metadata={"feed_source": label},
                        )
                    )
                # Delay entre requests para nao sobrecarregar feeds
                time.sleep(0.3)
            except Exception as e:
                self.logger.warning(f"Falha ao buscar feed '{label}': {e}")

        return events

    async def is_available(self) -> bool:
        try:
            import feedparser  # noqa: F401
            return True
        except ImportError:
            return False
