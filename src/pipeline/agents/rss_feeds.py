from src.pipeline.agents.base import BaseSourceAgent
from src.pipeline.models import TrendItem, TrendSource

DEFAULT_FEEDS = [
    "https://www.reddit.com/r/brasil/hot/.rss",
    "https://www.reddit.com/r/eu_nvr/hot/.rss",
    "https://www.reddit.com/r/memes/hot/.rss",
    "https://www.reddit.com/r/trees/hot/.rss",
    "https://www.reddit.com/r/StonerMemes/hot/.rss",
    "https://www.reddit.com/r/highdeas/hot/.rss",
    "https://www.sensacionalista.com.br/feed/",
]


class RSSFeedAgent(BaseSourceAgent):
    """Busca tópicos em alta de feeds RSS de humor e memes."""

    def __init__(self, feeds: list[str] | None = None, max_per_feed: int = 10):
        super().__init__("rss_feeds")
        self.feeds = feeds or DEFAULT_FEEDS
        self.max_per_feed = max_per_feed

    def fetch(self) -> list[TrendItem]:
        try:
            import feedparser
        except ImportError:
            self.logger.warning("feedparser não instalado, pulando RSS feeds")
            return []

        items = []
        for feed_url in self.feeds:
            try:
                feed = feedparser.parse(feed_url)
                for entry in feed.entries[: self.max_per_feed]:
                    item = TrendItem(
                        title=entry.get("title", ""),
                        source=TrendSource.RSS_FEED,
                        url=entry.get("link"),
                        score=0.3,
                    )
                    items.append(item)
            except Exception as e:
                self.logger.warning(f"Falha ao parsear feed {feed_url}: {e}")
        self.logger.info(f"Coletou {len(items)} itens de RSS feeds")
        return items

    def is_available(self) -> bool:
        try:
            import feedparser
            return True
        except ImportError:
            return False
