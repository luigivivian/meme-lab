from src.pipeline.agents.base import BaseSourceAgent
from src.pipeline.models import TrendItem, TrendSource


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
                # Estimar score baseado no tráfego
                score = 0.5
                if traffic:
                    traffic_str = str(traffic).replace("+", "").replace(",", "").replace(".", "")
                    # Extrair número
                    num = ""
                    for c in traffic_str:
                        if c.isdigit():
                            num += c
                    if num:
                        traffic_num = int(num)
                        if "K" in str(traffic) or "k" in str(traffic) or traffic_num >= 1000:
                            score = 0.7
                        if "M" in str(traffic) or traffic_num >= 100000:
                            score = 0.9

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
