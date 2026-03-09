import json
import re
import logging

from src.pipeline.models import TrendItem, AnalyzedTopic, TrendSource
from src.llm_client import generate_json

logger = logging.getLogger("clip-flow.analyzer")

ANALYZER_PROMPT = """Você é o curador de conteúdo para o "Gandalf Sincero" — um perfil de humor VIRAL
com frases engraçadas, leves e relatable no estilo memes brasileiros.

Abaixo está uma lista de tópicos em alta (trending). Sua tarefa:
1. Selecione os {count} melhores tópicos que rendem humor VIRAL, LEVE e ENGRAÇADO
2. Para cada tópico selecionado, forneça:
   - O tema adaptado para humor viral (gandalf_topic): transforme em algo do cotidiano, relatable
   - O ângulo de humor (humor_angle): como tornar isso engraçado e compartilhável
   - Uma nota de relevância de 0 a 1 (relevance_score)

Critérios de seleção (IMPORTANTES):
- PRIORIZE: temas do cotidiano, trabalho, internet, comida, relacionamentos, redes sociais
- PRIORIZE: temas que geram identificação ("sou eu"), risada e compartilhamento
- EVITE COMPLETAMENTE: tragédias, violência, guerras, mortes, política, religião
- EVITE: temas pesados, negativos, desmotivacionais ou que podem ofender
- Se um trend é sobre algo sério, TRANSFORME em algo leve do cotidiano relacionado

Responda APENAS em JSON válido, no formato:
[
  {{
    "original_title": "título original do trend",
    "gandalf_topic": "tema adaptado para humor viral e leve",
    "humor_angle": "ângulo engraçado e relatable",
    "relevance_score": 0.9
  }}
]"""


class ClaudeAnalyzer:
    """Usa Gemini para analisar trends e selecionar os melhores temas."""

    def analyze(self, trends: list[TrendItem], count: int = 5) -> list[AnalyzedTopic]:
        """Envia trends para Gemini e recebe tópicos curados para Gandalf Sincero."""
        trends_text = "\n".join(
            f"- {t.title} (fonte: {t.source.value}, tráfego: {t.traffic or 'N/A'})"
            for t in trends
        )

        prompt = ANALYZER_PROMPT.format(count=count)

        raw = generate_json(
            system_prompt=prompt,
            user_message=f"Tópicos em alta:\n{trends_text}",
            max_tokens=2048,
        )

        selections = self._parse_json(raw)

        # Mapear de volta para AnalyzedTopic
        trend_map = {t.title.lower().strip(): t for t in trends}
        analyzed = []
        for sel in selections:
            original_title = sel.get("original_title", "")
            original_trend = trend_map.get(original_title.lower().strip())
            if not original_trend:
                original_trend = TrendItem(
                    title=original_title,
                    source=TrendSource.GOOGLE_TRENDS,
                )
            analyzed.append(
                AnalyzedTopic(
                    original_trend=original_trend,
                    gandalf_topic=sel["gandalf_topic"],
                    humor_angle=sel.get("humor_angle", ""),
                    relevance_score=sel.get("relevance_score", 0.5),
                )
            )
        return analyzed

    def _parse_json(self, raw: str) -> list[dict]:
        """Parse JSON da resposta com fallbacks."""
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        if "```" in raw:
            match = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass

        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        logger.error(f"Não foi possível parsear JSON: {raw[:200]}")
        return []
