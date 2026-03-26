"""Lemmy Communities Agent — comunidades BR no Lemmy (Reddit federado).

Monitora comunidades brasileiras no Lemmy via API publica (sem autenticacao).
Conteudo diferenciado do Reddit — comunidades federadas com humor e memes BR.

Instancias monitoradas:
  - lemmy.world   — maior instancia global, comunidades "brasil" e "memes"
  - lemmy.eco.br  — instancia brasileira, comunidade "brasil"

Usa urllib.request (stdlib) para HTTP — sem dependencias extras.
"""

import asyncio
import json
import logging
import time
import urllib.request
import urllib.error

from config import LEMMY_MAX_POSTS
from src.pipeline.agents.async_base import AsyncSourceAgent
from src.pipeline.models_v2 import TrendEvent, TrendSource

logger = logging.getLogger("clip-flow.agent.lemmy")

# (instance_url, community_name, score_base)
_LEMMY_COMMUNITIES = [
    ("https://lemmy.world",  "brasil", 0.62),
    ("https://lemmy.world",  "memes",  0.58),
    ("https://lemmy.eco.br", "brasil", 0.65),
]

# Timeout para requests HTTP (segundos)
_HTTP_TIMEOUT = 15

# User-Agent para nao ser bloqueado
_USER_AGENT = "ClipFlow/1.0 (bot de memes BR; +https://github.com/clip-flow)"


class LemmyCommunitiesAgent(AsyncSourceAgent):
    """Comunidades brasileiras no Lemmy — API publica sem autenticacao."""

    def __init__(self, max_posts: int = LEMMY_MAX_POSTS):
        super().__init__("lemmy")
        self.max_posts = max_posts

    async def fetch(self) -> list[TrendEvent]:
        """Busca posts das comunidades Lemmy em thread separada."""
        try:
            events = await asyncio.to_thread(self._fetch_all)
            self.logger.info(f"Lemmy Communities: {len(events)} eventos coletados")
            return events
        except Exception as e:
            self.logger.error(f"Lemmy Communities falhou: {e}")
            return []

    def _fetch_all(self) -> list[TrendEvent]:
        """Busca todas as comunidades configuradas (sync)."""
        seen: set[str] = set()
        events: list[TrendEvent] = []

        for instance_url, community_name, score_base in _LEMMY_COMMUNITIES:
            try:
                posts = self._fetch_community(instance_url, community_name)
                for post in posts[:self.max_posts]:
                    title: str = post.get("name", "").strip()
                    if not title or len(title) < 5:
                        continue

                    title_lower = title.lower()
                    if title_lower in seen:
                        continue
                    seen.add(title_lower)

                    # Score normalizado: upvotes - downvotes, normalizado 0.0-1.0
                    raw_score = post.get("score", 0)
                    normalized_score = self._normalize_score(raw_score, score_base)

                    post_url = post.get("ap_id") or post.get("url")

                    events.append(
                        TrendEvent(
                            title=title,
                            source=TrendSource.LEMMY,
                            score=normalized_score,
                            category="humor",
                            url=post_url,
                            metadata={
                                "instance": instance_url,
                                "community": community_name,
                                "lemmy_score": raw_score,
                                "comments": post.get("counts", {}).get("comments", 0),
                            },
                        )
                    )

                # Delay entre requests para nao sobrecarregar instancias
                time.sleep(0.3)

            except Exception as e:
                self.logger.warning(
                    f"Falha ao buscar comunidade '{community_name}' em {instance_url}: {e}"
                )

        return events

    def _fetch_community(self, instance_url: str, community_name: str) -> list[dict]:
        """Busca posts de uma comunidade via API Lemmy v3."""
        api_url = (
            f"{instance_url}/api/v3/post/list"
            f"?community_name={community_name}&sort=Hot&limit=20"
        )

        req = urllib.request.Request(api_url)
        req.add_header("User-Agent", _USER_AGENT)
        req.add_header("Accept", "application/json")

        with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        # Resposta Lemmy: {"posts": [{"post": {...}, "counts": {...}}, ...]}
        raw_posts = data.get("posts", [])
        posts = []
        for item in raw_posts:
            post_data = item.get("post", {})
            counts = item.get("counts", {})
            # Mescla score e comments no dict do post para facilitar acesso
            post_data["score"] = counts.get("score", 0)
            post_data["counts"] = counts
            posts.append(post_data)

        self.logger.debug(
            f"Lemmy {instance_url}/c/{community_name}: {len(posts)} posts obtidos"
        )
        return posts

    @staticmethod
    def _normalize_score(raw_score: int, score_base: float) -> float:
        """Normaliza score do Lemmy para 0.0-1.0.

        Posts com score alto recebem boost sobre o score_base.
        Score maximo considerado: 500 (posts muito populares no Lemmy).
        """
        if raw_score <= 0:
            return max(score_base * 0.5, 0.0)

        # Normaliza 0-500 para 0.0-0.35 de bonus
        bonus = min(raw_score / 500.0, 1.0) * 0.35
        return min(score_base + bonus, 1.0)

    async def is_available(self) -> bool:
        """Sempre disponivel — usa apenas stdlib."""
        return True
