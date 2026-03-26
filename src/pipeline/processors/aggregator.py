import math
import re
import unicodedata
from datetime import datetime

from src.pipeline.models import TrendItem


class TrendAggregator:
    """Merge, dedup e ranking de trends de multiplas fontes.

    Features:
    - Multi-source boost: trends confirmed by 2+ sources get score multiplied
      by (1 + 0.2 * (sources - 1)), capped at 2.0x
    - Temporal decay: exponential decay e^(-age_hours / 24) so fresh content
      ranks higher (24h-old trends drop to ~37% of original score)
    """

    def __init__(self, max_topics: int = 20):
        self.max_topics = max_topics

    def aggregate(self, all_trends: list[TrendItem]) -> list[TrendItem]:
        """Merge todas as trends, remove duplicatas, aplica boost e decay, ordena por score."""
        if not all_trends:
            return []

        seen: dict[str, TrendItem] = {}
        source_counts: dict[str, int] = {}  # track source count per normalized title

        for trend in all_trends:
            key = self._normalize(trend.title)
            if not key:
                continue
            if key in seen:
                # Track multi-source appearances
                source_counts[key] = source_counts.get(key, 1) + 1
                # Keep highest base score
                if trend.score > seen[key].score:
                    seen[key].score = trend.score
            else:
                seen[key] = trend
                source_counts[key] = 1

        # Apply multi-source boost: score *= (1 + 0.2 * (sources - 1)), cap at 2.0x
        for key, trend in seen.items():
            sources = source_counts.get(key, 1)
            if sources > 1:
                boost = min(1.0 + 0.2 * (sources - 1), 2.0)
                trend.score = min(round(trend.score * boost, 3), 1.0)

        ranked = list(seen.values())

        # Apply temporal decay
        self._apply_temporal_decay(ranked)

        # Sort by decayed+boosted score
        ranked.sort(key=lambda t: t.score, reverse=True)
        return ranked[: self.max_topics]

    def _apply_temporal_decay(self, trends: list[TrendItem]) -> None:
        """Apply exponential decay: score *= e^(-age_hours / 24).

        Fresh trends (< 2h) keep ~92% of score.
        24h-old trends drop to ~37%.
        48h-old trends drop to ~14%.
        """
        now = datetime.now()
        for trend in trends:
            age_hours = (now - trend.fetched_at).total_seconds() / 3600.0
            if age_hours < 0:
                age_hours = 0
            decay_factor = math.exp(-age_hours / 24.0)
            trend.score = round(trend.score * decay_factor, 3)

    def _normalize(self, text: str) -> str:
        """Normaliza texto para comparacao de duplicatas."""
        text = text.lower().strip()
        # Remover acentos
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
