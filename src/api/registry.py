"""Registry unificado de agents — fonte unica de verdade."""

import asyncio
import importlib
import logging

logger = logging.getLogger("clip-flow.api")

# Agents ativos (name, module_path, class_name, is_async)
AGENT_REGISTRY: list[tuple[str, str, str, bool]] = [
    ("google_trends", "src.pipeline.agents.google_trends", "GoogleTrendsAgent", False),
    ("reddit_memes", "src.pipeline.agents.reddit_memes", "RedditMemesAgent", False),
    ("rss_feeds", "src.pipeline.agents.rss_feeds", "RSSFeedAgent", False),
    ("youtube_rss", "src.pipeline.agents.youtube_rss", "YouTubeRSSAgent", True),
    ("gemini_web_trends", "src.pipeline.agents.gemini_web_trends", "GeminiWebTrendsAgent", True),
    ("brazil_viral_rss", "src.pipeline.agents.brazil_viral_rss", "BrazilViralRSSAgent", True),
    ("bluesky_trends", "src.pipeline.agents.bluesky_trends", "BlueSkyTrendsAgent", True),
    ("hackernews", "src.pipeline.agents.hackernews", "HackerNewsAgent", True),
    ("lemmy_communities", "src.pipeline.agents.lemmy_communities", "LemmyCommunitiesAgent", True),
]

# Stubs (requerem API key paga)
STUB_AGENTS: list[tuple[str, str, str]] = [
    ("tiktok_trends", "src.pipeline.agents.tiktok_trends", "TikTokTrendsAgent"),
    ("instagram_explore", "src.pipeline.agents.instagram_explore", "InstagramExploreAgent"),
    ("twitter_x", "src.pipeline.agents.twitter_x", "TwitterXAgent"),
    ("facebook_viral", "src.pipeline.agents.facebook_viral", "FacebookViralAgent"),
    ("youtube_shorts", "src.pipeline.agents.youtube_shorts", "YouTubeShortsAgent"),
]

WORKER_NAMES = ["phrase_worker", "image_worker", "caption_worker", "hashtag_worker", "quality_worker"]


def get_agent_map() -> dict[str, tuple[str, str, bool]]:
    """Retorna dict name -> (module_path, class_name, is_async)."""
    return {name: (mod, cls, is_async) for name, mod, cls, is_async in AGENT_REGISTRY}


def instantiate_agent(name: str):
    """Importa e instancia um agent pelo nome. Retorna None se nao encontrado."""
    agent_map = get_agent_map()
    if name not in agent_map:
        return None
    module_path, class_name, _ = agent_map[name]
    mod = importlib.import_module(module_path)
    cls = getattr(mod, class_name)
    return cls()


async def check_agent_availability(name: str, module_path: str, class_name: str) -> bool:
    """Checa disponibilidade de um agent (sync ou async)."""
    try:
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        result = cls().is_available()
        return (await result) if asyncio.iscoroutine(result) else result
    except Exception:
        return False


async def fetch_agent(name: str, module_path: str, class_name: str, is_async: bool):
    """Executa fetch de um agent. Retorna lista de items."""
    mod = importlib.import_module(module_path)
    cls = getattr(mod, class_name)
    agent = cls()
    result = agent.fetch()
    if asyncio.iscoroutine(result):
        return await result
    return await asyncio.to_thread(lambda: result) if not is_async else result
