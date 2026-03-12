"""BlueSky Trends Agent — busca posts virais brasileiros via AT Protocol.

Usa autenticacao via app password para acessar a API de busca do BlueSky.
Requer BLUESKY_HANDLE e BLUESKY_APP_PASSWORD no .env.

Criar app password em: https://bsky.app/settings/app-passwords
"""

import asyncio
import json
import logging
import urllib.request
import urllib.parse
from datetime import datetime

from config import BLUESKY_MAX_POSTS, BLUESKY_HANDLE, BLUESKY_APP_PASSWORD
from src.pipeline.agents.async_base import AsyncSourceAgent
from src.pipeline.models_v2 import TrendEvent, TrendSource

logger = logging.getLogger("clip-flow.agent.bluesky")

# Endpoints do AT Protocol
_API_BASE = "https://bsky.social/xrpc"
_PUBLIC_BASE = "https://public.api.bsky.app/xrpc"
_CREATE_SESSION = f"{_API_BASE}/com.atproto.server.createSession"
_SEARCH_POSTS = f"{_API_BASE}/app.bsky.feed.searchPosts"

# Keywords para buscar conteudo viral BR
_KEYWORDS_BR = [
    "meme viral",
    "zoeira brasileira",
    "humor brasileiro",
    "engraçado demais",
    "kkkkk",
    "socorro mano",
    "não aguento mais",
    "piada do dia",
]

_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "clip-flow/1.0 (memelab pipeline)",
}


class BlueSkyTrendsAgent(AsyncSourceAgent):
    """Busca posts virais brasileiros no BlueSky via AT Protocol com autenticacao."""

    def __init__(self, max_posts: int = BLUESKY_MAX_POSTS):
        super().__init__("bluesky_trends")
        self.max_posts = max_posts
        self._access_jwt: str | None = None

    async def fetch(self) -> list[TrendEvent]:
        """Busca posts virais do BlueSky em paralelo por keyword."""
        try:
            events = await asyncio.to_thread(self._fetch_all)
            self.logger.info(f"BlueSky Trends: {len(events)} eventos coletados")
            return events
        except Exception as e:
            self.logger.error(f"BlueSky Trends falhou: {e}")
            return []

    def _authenticate(self) -> bool:
        """Autentica via createSession e obtem JWT token."""
        if not BLUESKY_HANDLE or not BLUESKY_APP_PASSWORD:
            self.logger.warning("BlueSky: BLUESKY_HANDLE ou BLUESKY_APP_PASSWORD nao configurados no .env")
            return False

        try:
            body = json.dumps({
                "identifier": BLUESKY_HANDLE,
                "password": BLUESKY_APP_PASSWORD,
            }).encode("utf-8")

            req = urllib.request.Request(_CREATE_SESSION, data=body, headers=_HEADERS, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self._access_jwt = data.get("accessJwt")
                self.logger.info(f"BlueSky: autenticado como {data.get('handle', BLUESKY_HANDLE)}")
                return bool(self._access_jwt)
        except Exception as e:
            self.logger.error(f"BlueSky auth falhou: {e}")
            return False

    def _fetch_all(self) -> list[TrendEvent]:
        """Busca sincronamente posts de todas as keywords e retorna eventos unicos."""
        if not self._authenticate():
            return []

        seen: set[str] = set()
        all_events: list[TrendEvent] = []

        for keyword in _KEYWORDS_BR:
            try:
                posts = self._search_posts(keyword)
                for post in posts:
                    text = post.get("text", "").strip()
                    if not text or len(text) < 10:
                        continue

                    # Dedup por texto (lowercase)
                    text_key = text.lower()[:100]
                    if text_key in seen:
                        continue
                    seen.add(text_key)

                    # Calcular engajamento
                    likes = post.get("like_count", 0)
                    reposts = post.get("repost_count", 0)
                    replies = post.get("reply_count", 0)
                    engagement = likes + reposts

                    # Titulo: truncar texto longo
                    title = text if len(text) <= 120 else text[:117] + "..."

                    # URI do post para montar URL
                    uri = post.get("uri", "")
                    author_handle = post.get("author_handle", "")
                    post_url = self._build_post_url(uri, author_handle)

                    all_events.append(
                        TrendEvent(
                            title=title,
                            source=TrendSource.BLUESKY,
                            score=0.0,  # normalizado depois
                            category="humor",
                            url=post_url,
                            metadata={
                                "platform": "bluesky",
                                "keyword": keyword,
                                "likes": likes,
                                "reposts": reposts,
                                "replies": replies,
                                "engagement": engagement,
                                "author": author_handle,
                            },
                        )
                    )
            except Exception as e:
                self.logger.warning(f"Falha ao buscar keyword '{keyword}': {e}")

        # Ordenar por engajamento e limitar
        all_events.sort(
            key=lambda e: e.metadata.get("engagement", 0), reverse=True
        )
        all_events = all_events[: self.max_posts]

        # Normalizar scores 0.0-1.0 baseado no engajamento
        self._normalize_scores(all_events)

        return all_events

    def _search_posts(self, keyword: str) -> list[dict]:
        """Busca posts no BlueSky para uma keyword especifica (autenticado)."""
        params = urllib.parse.urlencode({
            "q": keyword,
            "lang": "pt",
            "limit": 25,
            "sort": "top",
        })
        url = f"{_SEARCH_POSTS}?{params}"

        headers = {**_HEADERS}
        if self._access_jwt:
            headers["Authorization"] = f"Bearer {self._access_jwt}"

        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        posts = []
        for item in data.get("posts", []):
            record = item.get("record", {})
            author = item.get("author", {})
            posts.append({
                "text": record.get("text", ""),
                "like_count": item.get("likeCount", 0),
                "repost_count": item.get("repostCount", 0),
                "reply_count": item.get("replyCount", 0),
                "uri": item.get("uri", ""),
                "author_handle": author.get("handle", ""),
                "created_at": record.get("createdAt", ""),
            })

        return posts

    def _build_post_url(self, uri: str, handle: str) -> str | None:
        """Constroi URL web do post a partir do AT URI."""
        # URI formato: at://did:plc:xxx/app.bsky.feed.post/yyy
        if not uri or not handle:
            return None
        parts = uri.split("/")
        if len(parts) >= 5:
            post_id = parts[-1]
            return f"https://bsky.app/profile/{handle}/post/{post_id}"
        return None

    def _normalize_scores(self, events: list[TrendEvent]) -> None:
        """Normaliza scores de 0.0 a 1.0 baseado no engajamento maximo."""
        if not events:
            return

        max_engagement = max(
            e.metadata.get("engagement", 0) for e in events
        )
        if max_engagement == 0:
            for e in events:
                e.score = 0.3
            return

        for e in events:
            engagement = e.metadata.get("engagement", 0)
            e.score = 0.3 + 0.6 * (engagement / max_engagement)

    async def is_available(self) -> bool:
        """Disponivel se credenciais configuradas."""
        return bool(BLUESKY_HANDLE and BLUESKY_APP_PASSWORD)
