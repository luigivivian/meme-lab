import json
import re
import logging

from src.pipeline.models import TrendItem, AnalyzedTopic, TrendSource
from src.llm_client import generate_json

logger = logging.getLogger("clip-flow.analyzer")

ANALYZER_PROMPT = """Você é o curador de conteúdo para o "Mago Mestre" — um bruxo velho e sábio que posta
memes virais com humor brasileiro. Ele já viu de tudo na vida e comenta o cotidiano com sabedoria cômica.

Abaixo está uma lista de tópicos em alta (trending). Sua tarefa:
1. Filtre APENAS tópicos que rendem MEMES virais (ignore notícias sérias, política, tragédias)
2. Selecione até {count} tópicos que combinem com humor do cotidiano, preguiça, comida, etc.
3. Se NENHUM trend for bom para meme, use temas CLICHÊ que sempre funcionam (veja abaixo)

Para cada tópico, forneça:
   - gandalf_topic: tema adaptado para humor do mago sábio
   - humor_angle: como tornar isso engraçado (perspectiva do velho sábio zoeiro)
   - relevance_score: 0 a 1

TEMAS CLICHÊ (use quando os trends não prestam):
- Fome de madrugada, delivery 3h da manhã
- Segunda-feira vs ficar em casa
- Cancelar planos pra ficar deitado
- Geladeira vazia, miojo gourmet, dieta que nunca começa
- Pensamentos aleatórios de madrugada
- Preguiça extrema, dormir 14h, alarme ignorado
- WiFi caiu e a fome bateu junto
- Procrastinação, "amanhã eu faço"
- Café como combustível de vida

PRIORIZE:
- Memes, humor, coisas engraçadas e relatables
- Temas do cotidiano: preguiça, comida, trabalho, tecnologia, relacionamentos
- Coisas banais que ficam engraçadas com perspectiva de sábio

EVITE COMPLETAMENTE:
- Notícias sérias, política, religião, tragédias, violência
- Qualquer coisa que não renda meme engraçado
- Temas pesados ou polêmicos

IMPORTANTE: Se nenhum trend é bom, INVENTE temas clichê dos listados acima.
Retorne SEMPRE {count} itens, nunca zero.

Responda APENAS em JSON válido:
[
  {{
    "original_title": "título original do trend (ou 'cliche' se inventado)",
    "gandalf_topic": "tema adaptado para o mago sábio",
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
            max_tokens=4096,
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
