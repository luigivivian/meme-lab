"""Modelos enriquecidos para o pipeline multi-agente event-driven.

Estende os modelos existentes em models.py sem modifica-los.
Funcoes conversoras fazem a ponte entre TrendItem <-> TrendEvent.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from src.pipeline.models import TrendItem, TrendSource as _OldTrendSource, AnalyzedTopic


class TrendSource(Enum):
    """Fontes de trend — estende o enum original com novas plataformas."""
    GOOGLE_TRENDS = "google_trends"
    REDDIT = "reddit"
    RSS_FEED = "rss_feed"
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    TWITTER_X = "twitter_x"
    FACEBOOK = "facebook"
    YOUTUBE = "youtube"


@dataclass
class TrendEvent:
    """Evento enriquecido de trend para o broker."""
    title: str
    source: TrendSource
    score: float = 0.0
    velocity: float = 0.0
    category: str = "geral"
    sentiment: str = "neutro"
    traffic: str | None = None
    url: str | None = None
    related_keywords: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    sources_count: int = 1
    fetched_at: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])


@dataclass
class WorkOrder:
    """Ordem de trabalho emitida pelo curador para a camada de geracao."""
    order_id: str
    trend_event: TrendEvent
    gandalf_topic: str
    humor_angle: str
    situacao_key: str
    relevance_score: float
    priority: int = 0
    phrases_count: int = 1
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ContentPackage:
    """Pacote final de conteudo pronto para publicacao."""
    phrase: str
    image_path: str
    topic: str
    source: TrendSource
    caption: str = ""
    hashtags: list[str] = field(default_factory=list)
    best_time_to_post: str | None = None
    quality_score: float = 0.0
    work_order: WorkOrder | None = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class AgentPipelineResult:
    """Resultado do pipeline multi-agente."""
    trends_fetched: int = 0
    trend_events_queued: int = 0
    work_orders_emitted: int = 0
    images_generated: int = 0
    packages_produced: int = 0
    content: list[ContentPackage] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    agent_stats: dict[str, dict] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None


# ===== Funcoes conversoras =====

# Mapa entre enums antigo e novo
_SOURCE_MAP = {
    _OldTrendSource.GOOGLE_TRENDS: TrendSource.GOOGLE_TRENDS,
    _OldTrendSource.REDDIT: TrendSource.REDDIT,
    _OldTrendSource.RSS_FEED: TrendSource.RSS_FEED,
}

_SOURCE_MAP_REVERSE = {v: k for k, v in _SOURCE_MAP.items()}


def trend_item_to_event(item: TrendItem) -> TrendEvent:
    """Converte TrendItem (modelo antigo) para TrendEvent (modelo novo)."""
    return TrendEvent(
        title=item.title,
        source=_SOURCE_MAP.get(item.source, TrendSource.RSS_FEED),
        score=item.score,
        traffic=item.traffic,
        url=item.url,
        related_keywords=item.related_keywords.copy(),
        fetched_at=item.fetched_at,
    )


def event_to_trend_item(event: TrendEvent) -> TrendItem:
    """Converte TrendEvent (modelo novo) para TrendItem (modelo antigo)."""
    old_source = _SOURCE_MAP_REVERSE.get(event.source, _OldTrendSource.RSS_FEED)
    return TrendItem(
        title=event.title,
        source=old_source,
        traffic=event.traffic,
        score=event.score,
        url=event.url,
        related_keywords=event.related_keywords.copy(),
        fetched_at=event.fetched_at,
    )
