from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TrendSource(Enum):
    GOOGLE_TRENDS = "google_trends"
    REDDIT = "reddit"
    RSS_FEED = "rss_feed"


@dataclass
class TrendItem:
    """Um tópico em alta de qualquer fonte."""
    title: str
    source: TrendSource
    traffic: str | None = None
    score: float = 0.0
    url: str | None = None
    related_keywords: list[str] = field(default_factory=list)
    fetched_at: datetime = field(default_factory=datetime.now)


@dataclass
class AnalyzedTopic:
    """Tópico após análise do Claude, pronto para geração de frases."""
    original_trend: TrendItem
    gandalf_topic: str
    humor_angle: str
    relevance_score: float


@dataclass
class GeneratedContent:
    """Conteúdo finalizado (frase + imagem)."""
    phrase: str
    image_path: str
    topic: str
    source: TrendSource
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class PipelineResult:
    """Resultado completo de uma execução do pipeline."""
    trends_fetched: int
    topics_analyzed: int
    images_generated: int
    content: list[GeneratedContent] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    finished_at: datetime | None = None
