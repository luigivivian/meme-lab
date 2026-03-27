import re

from src.pipeline.agents.base import BaseSourceAgent
from src.pipeline.models import TrendItem, TrendSource


def _parse_traffic(traffic_str: str) -> float:
    """Parse traffic string like '10K+', '1.5M+', '500' into a numeric value.

    Returns a score between 0.0 and 1.0 based on traffic magnitude.
    """
    if not traffic_str:
        return 0.5  # default when no traffic data

    clean = str(traffic_str).replace("+", "").replace(",", "").strip()
    match = re.search(r'(\d+\.?\d*)\s*([KMBkmb]?)', clean)
    if not match:
        return 0.5

    number = float(match.group(1))
    suffix = match.group(2).upper()

    multipliers = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}
    traffic_num = number * multipliers.get(suffix, 1)

    # Score mapping: <1K -> 0.4, 1K-10K -> 0.5, 10K-100K -> 0.6,
    # 100K-1M -> 0.7, 1M-10M -> 0.8, 10M+ -> 0.95
    if traffic_num >= 10_000_000:
        return 0.95
    elif traffic_num >= 1_000_000:
        return 0.85
    elif traffic_num >= 100_000:
        return 0.7
    elif traffic_num >= 10_000:
        return 0.6
    elif traffic_num >= 1_000:
        return 0.5
    else:
        return 0.4


class GoogleTrendsAgent(BaseSourceAgent):
    """Busca trending searches do Google Trends via trendspyg RSS."""

    def __init__(self, geo: str = "BR"):
        super().__init__("google_trends")
        self.geo = geo

    def fetch(self) -> list[TrendItem]:
        try:
            from trendspyg import download_google_trends_rss
        except ImportError:
            self.logger.warning("trendspyg não instalado, pulando Google Trends")
            return []

        try:
            trends = download_google_trends_rss(geo=self.geo)
            items = []
            for trend in trends:
                traffic = trend.get("traffic", "")
                score = _parse_traffic(traffic)

                item = TrendItem(
                    title=trend.get("trend", trend.get("title", "")),
                    source=TrendSource.GOOGLE_TRENDS,
                    traffic=str(traffic) if traffic else None,
                    score=score,
                    url=trend.get("url"),
                )
                items.append(item)
            self.logger.info(f"Coletou {len(items)} trends do Google Trends ({self.geo})")
            return items
        except Exception as e:
            self.logger.error(f"Falha ao buscar Google Trends: {e}")
            return []

    def is_available(self) -> bool:
        try:
            import trendspyg
            return True
        except ImportError:
            return False
