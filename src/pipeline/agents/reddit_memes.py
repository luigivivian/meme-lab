import time

from src.pipeline.agents.base import BaseSourceAgent
from src.pipeline.models import TrendItem, TrendSource

DEFAULT_SUBREDDITS = [
    # BR subs — high relevance
    ("DiretoDoZapZap", 0.6),
    ("tiodopave", 0.6),
    ("desabafos", 0.6),
    ("antitrampo", 0.6),
    # Cannabis BR
    ("maconha", 0.6),
    ("cultivonha", 0.6),
    # English/mixed subs — lower relevance
    ("trees", 0.3),
    ("microgrowery", 0.3),
]


class RedditMemesAgent(BaseSourceAgent):
    """Busca posts em alta do Reddit via RSS (sem auth necessaria). BR-first scoring."""

    def __init__(self, subreddits: list[tuple[str, float]] | None = None, limit_per_sub: int = 10):
        super().__init__("reddit_memes")
        self.subreddits = subreddits or DEFAULT_SUBREDDITS
        self.limit_per_sub = limit_per_sub

    def fetch(self) -> list[TrendItem]:
        try:
            import feedparser
        except ImportError:
            self.logger.warning("feedparser nao instalado, pulando Reddit")
            return []

        items = []
        for subreddit, base_score in self.subreddits:
            try:
                posts = self._fetch_subreddit(subreddit, base_score)
                items.extend(posts)
                time.sleep(0.5)
            except Exception as e:
                self.logger.warning(f"Falha ao buscar r/{subreddit}: {e}")
        self.logger.info(f"Coletou {len(items)} posts do Reddit")
        return items

    def _fetch_subreddit(self, subreddit: str, base_score: float) -> list[TrendItem]:
        import re as _re

        import feedparser

        url = f"https://www.reddit.com/r/{subreddit}/top/.rss?t=day"
        feed = feedparser.parse(url)

        # First pass: collect entries with upvote counts from content HTML
        entries_with_scores: list[tuple] = []
        for entry in feed.entries[: self.limit_per_sub]:
            title = entry.get("title", "").strip()
            if not title or len(title) < 10:
                continue
            # Try to extract upvotes from Reddit RSS content HTML
            content_html = ""
            content_list = entry.get("content", [])
            if content_list and isinstance(content_list, list):
                content_html = content_list[0].get("value", "") if content_list[0] else ""
            match = _re.search(r'(\d+)\s*points?', content_html)
            upvotes = int(match.group(1)) if match else None
            entries_with_scores.append((entry, title, upvotes))

        if not entries_with_scores:
            return []

        # Find max upvotes for relative scoring
        upvote_values = [u for _, _, u in entries_with_scores if u is not None]
        max_upvotes = max(upvote_values) if upvote_values else 0

        items = []
        for position, (entry, title, upvotes) in enumerate(entries_with_scores):
            if max_upvotes > 0 and upvotes is not None:
                # Engagement-based: base_score * (0.5 + 0.5 * (upvotes / max_upvotes))
                score = round(base_score * (0.5 + 0.5 * (upvotes / max_upvotes)), 3)
            else:
                # Position-based fallback: first items score higher
                score = round(max(base_score - (position * 0.02), base_score * 0.5), 3)

            item = TrendItem(
                title=title,
                source=TrendSource.REDDIT,
                url=entry.get("link"),
                score=score,
            )
            items.append(item)
        return items

    def is_available(self) -> bool:
        try:
            import feedparser
            return True
        except ImportError:
            return False
