"""HackerNews Top Stories Agent — busca historias populares via Firebase API publica.

Monitora as top stories do Hacker News para captar trends de tecnologia,
startups, e cultura geek que podem virar memes relataveis.

API publica (sem autenticacao):
  - Top stories: https://hacker-news.firebaseio.com/v0/topstories.json
  - Item detail: https://hacker-news.firebaseio.com/v0/item/{id}.json

Filtro: score minimo 50 para descartar itens de baixa relevancia.
Score normalizado: divide pelo maior score do batch (0.0-1.0).
"""

import asyncio
import json
import logging
import urllib.request

from config import HACKERNEWS_MAX_STORIES
from src.pipeline.agents.async_base import AsyncSourceAgent
from src.pipeline.models_v2 import TrendEvent, TrendSource

logger = logging.getLogger("clip-flow.agent.hackernews")

_TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{item_id}.json"

# Score minimo do HN para considerar relevante
_MIN_SCORE = 50

# Timeout em segundos para requests HTTP
_REQUEST_TIMEOUT = 15


class HackerNewsAgent(AsyncSourceAgent):
    """Busca top stories do Hacker News via Firebase API publica."""

    def __init__(self, max_stories: int = HACKERNEWS_MAX_STORIES):
        super().__init__("hackernews")
        self.max_stories = max_stories

    async def fetch(self) -> list[TrendEvent]:
        """Busca top stories e retorna lista de TrendEvent."""
        try:
            events = await asyncio.to_thread(self._fetch_all)
            self.logger.info(f"HackerNews: {len(events)} stories coletadas")
            return events
        except Exception as e:
            self.logger.error(f"HackerNews falhou: {e}")
            return []

    def _fetch_all(self) -> list[TrendEvent]:
        """Busca top story IDs e depois detalhes de cada item."""
        # Buscar IDs das top stories
        story_ids = self._http_get_json(_TOP_STORIES_URL)
        if not story_ids or not isinstance(story_ids, list):
            self.logger.warning("Nenhum story ID retornado pela API do HN")
            return []

        # Limitar ao maximo configurado
        story_ids = story_ids[: self.max_stories]

        # Buscar detalhes de cada story
        items: list[dict] = []
        for story_id in story_ids:
            try:
                url = _ITEM_URL.format(item_id=story_id)
                item = self._http_get_json(url)
                if item and isinstance(item, dict):
                    items.append(item)
            except Exception as e:
                self.logger.debug(f"Falha ao buscar item {story_id}: {e}")

        if not items:
            self.logger.warning("Nenhum item retornado do HN")
            return []

        # Filtrar por score minimo
        items = [i for i in items if i.get("score", 0) >= _MIN_SCORE]

        if not items:
            self.logger.info("Nenhum item acima do score minimo")
            return []

        # Normalizar scores: dividir pelo maior score do batch
        max_score = max(i.get("score", 1) for i in items)
        if max_score <= 0:
            max_score = 1

        events: list[TrendEvent] = []
        for item in items:
            title = (item.get("title") or "").strip()
            if not title:
                continue

            raw_score = item.get("score", 0)
            normalized_score = min(max(raw_score / max_score, 0.0), 1.0)

            item_url = item.get("url") or f"https://news.ycombinator.com/item?id={item.get('id', '')}"

            events.append(
                TrendEvent(
                    title=title,
                    source=TrendSource.HACKERNEWS,
                    score=round(normalized_score, 3),
                    category="tecnologia",
                    url=item_url,
                    metadata={
                        "hn_id": item.get("id"),
                        "hn_score": raw_score,
                        "hn_comments": item.get("descendants", 0),
                        "hn_by": item.get("by", ""),
                    },
                )
            )

        self.logger.debug(f"HN: {len(events)} stories apos filtro (min_score={_MIN_SCORE})")
        return events

    @staticmethod
    def _http_get_json(url: str) -> dict | list | None:
        """Faz GET HTTP e retorna JSON parseado. Retorna None em caso de erro."""
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "clip-flow/1.0 (HackerNews Agent)"},
            )
            with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

    async def is_available(self) -> bool:
        """Sempre disponivel — usa stdlib, sem dependencias externas."""
        return True
