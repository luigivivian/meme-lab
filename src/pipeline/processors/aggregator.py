import re
import unicodedata

from src.pipeline.models import TrendItem


class TrendAggregator:
    """Merge, dedup e ranking de trends de múltiplas fontes."""

    def __init__(self, max_topics: int = 20):
        self.max_topics = max_topics

    def aggregate(self, all_trends: list[TrendItem]) -> list[TrendItem]:
        """Merge todas as trends, remove duplicatas, ordena por score."""
        if not all_trends:
            return []

        seen: dict[str, TrendItem] = {}
        for trend in all_trends:
            key = self._normalize(trend.title)
            if not key:
                continue
            if key in seen:
                # Boost se tópico aparece em múltiplas fontes
                seen[key].score = min(seen[key].score + 0.2, 1.0)
            else:
                seen[key] = trend

        ranked = sorted(seen.values(), key=lambda t: t.score, reverse=True)
        return ranked[: self.max_topics]

    def _normalize(self, text: str) -> str:
        """Normaliza texto para comparação de duplicatas."""
        text = text.lower().strip()
        # Remover acentos
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
        text = re.sub(r"[^\w\s]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()
