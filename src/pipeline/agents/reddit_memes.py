import time

from src.pipeline.agents.base import BaseSourceAgent
from src.pipeline.models import TrendItem, TrendSource

DEFAULT_SUBREDDITS = [
    "brasil",
    "eu_nvr",
    "DiretoDoZapZap",
    "memes",
    "dankmemes",
    "meirl",
    "me_irl",
    "funny",
]


class RedditMemesAgent(BaseSourceAgent):
    """Busca posts em alta do Reddit via RSS (sem auth necessária)."""

    def __init__(self, subreddits: list[str] | None = None, limit_per_sub: int = 10):
        super().__init__("reddit_memes")
        self.subreddits = subreddits or DEFAULT_SUBREDDITS
        self.limit_per_sub = limit_per_sub

    def fetch(self) -> list[TrendItem]:
        try:
            import feedparser
        except ImportError:
            self.logger.warning("feedparser não instalado, pulando Reddit")
            return []

        items = []
        for subreddit in self.subreddits:
            try:
                posts = self._fetch_subreddit(subreddit)
                items.extend(posts)
                time.sleep(0.5)
            except Exception as e:
                self.logger.warning(f"Falha ao buscar r/{subreddit}: {e}")
        self.logger.info(f"Coletou {len(items)} posts do Reddit")
        return items

    def _fetch_subreddit(self, subreddit: str) -> list[TrendItem]:
        import feedparser

        url = f"https://www.reddit.com/r/{subreddit}/hot/.rss"
        feed = feedparser.parse(url)

        items = []
        for entry in feed.entries[: self.limit_per_sub]:
            title = entry.get("title", "")
            if not title:
                continue
            item = TrendItem(
                title=title,
                source=TrendSource.REDDIT,
                url=entry.get("link"),
                score=0.4,
            )
            items.append(item)
        return items

    def is_available(self) -> bool:
        try:
            import feedparser
            return True
        except ImportError:
            return False
