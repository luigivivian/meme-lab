import json
import re
import logging
import time

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


OLLAMA_SINGLE_PROMPT = """Voce e o curador de conteudo para o "Mago Mestre" — um bruxo velho e sabio que posta memes virais com humor brasileiro.

Analise este topico trending e decida se rende um MEME engraçado.
Se sim, adapte para o humor do mago. Se nao, invente um tema cliche engraçado.

TEMAS CLICHE (use se o trend nao presta): fome de madrugada, segunda-feira, cancelar planos, preguica, wifi caiu, cafe, procrastinacao, sono.

EVITE: politica, religiao, tragedias, violencia, noticias serias.

Responda com UM objeto JSON:
{{"original_title": "titulo original", "gandalf_topic": "tema adaptado", "humor_angle": "angulo engraçado", "relevance_score": 0.9}}"""


class ClaudeAnalyzer:
    """Analisa trends e seleciona melhores temas. Suporta Ollama e Gemini."""

    def analyze(self, trends: list[TrendItem], count: int = 5) -> list[AnalyzedTopic]:
        """Envia trends para LLM e recebe topicos curados."""
        from config import LLM_BACKEND

        logger.info(f"Analyzer recebeu {len(trends)} trends, selecionando {count}")

        if LLM_BACKEND == "ollama":
            return self._analyze_ollama(trends, count)
        return self._analyze_gemini(trends, count)

    def _analyze_ollama(self, trends: list[TrendItem], count: int) -> list[AnalyzedTopic]:
        """Analise via Ollama — uma chamada por trend (gemma3 retorna 1 objeto por vez)."""
        from config import OLLAMA_MODEL, GEMINI_MODEL_NORMAL

        t0 = time.perf_counter()

        # Pre-selecionar os melhores trends por score/trafego (evita N chamadas desnecessarias)
        candidates = sorted(
            trends,
            key=lambda t: float(t.traffic.replace("+", "").replace(",", "")) if t.traffic and t.traffic.replace("+", "").replace(",", "").isdigit() else 0,
            reverse=True,
        )[:count * 2]  # pegar 2x para ter margem

        logger.info(
            f"Analyzer Ollama ({OLLAMA_MODEL}): {len(candidates)} candidatos "
            f"(de {len(trends)} trends), gerando {count} temas..."
        )

        selections = []
        errors = 0
        for i, trend in enumerate(candidates):
            if len(selections) >= count:
                break
            try:
                call_t0 = time.perf_counter()
                raw = generate_json(
                    system_prompt=OLLAMA_SINGLE_PROMPT,
                    user_message=f"Topico trending: {trend.title} (fonte: {trend.source.value}, trafego: {trend.traffic or 'N/A'})",
                    max_tokens=512,
                    tier="normal",
                )
                call_elapsed = time.perf_counter() - call_t0

                parsed = self._parse_json(raw)
                if parsed:
                    sel = parsed[0]
                    selections.append(sel)
                    logger.info(
                        f"  [{i+1}/{len(candidates)}] Ollama {call_elapsed:.1f}s: "
                        f"'{sel.get('gandalf_topic', '?')}' score={sel.get('relevance_score', 0):.2f}"
                    )
                else:
                    errors += 1
                    logger.warning(f"  [{i+1}/{len(candidates)}] Ollama parse falhou: {raw[:100]}")
            except Exception as e:
                errors += 1
                logger.warning(f"  [{i+1}/{len(candidates)}] Ollama erro: {type(e).__name__}: {e}")

        elapsed = time.perf_counter() - t0

        # Se Ollama nao conseguiu nada, tenta Gemini como fallback
        if not selections:
            logger.warning(f"Analyzer Ollama falhou em todos ({errors} erros em {elapsed:.1f}s), tentando Gemini fallback...")
            try:
                return self._analyze_gemini(trends, count)
            except Exception as e2:
                logger.error(f"Analyzer Gemini fallback tambem falhou: {type(e2).__name__}: {e2}")

        logger.info(
            f"Analyzer Ollama concluido em {elapsed:.1f}s: "
            f"{len(selections)} temas, {errors} erros"
        )

        return self._selections_to_topics(selections, trends, f"ollama ({OLLAMA_MODEL})")

    def _analyze_gemini(self, trends: list[TrendItem], count: int) -> list[AnalyzedTopic]:
        """Analise via Gemini — uma chamada com todos os trends (JSON array confiavel)."""
        from config import GEMINI_MODEL_NORMAL

        trends_text = "\n".join(
            f"- {t.title} (fonte: {t.source.value}, tráfego: {t.traffic or 'N/A'})"
            for t in trends
        )
        prompt = ANALYZER_PROMPT.format(count=count)

        t0 = time.perf_counter()
        logger.info(f"Analyzer usando Gemini ({GEMINI_MODEL_NORMAL})...")
        raw = generate_json(
            system_prompt=prompt,
            user_message=f"Tópicos em alta:\n{trends_text}",
            max_tokens=4096,
            tier="normal",
        )
        elapsed = time.perf_counter() - t0
        backend_used = f"gemini ({GEMINI_MODEL_NORMAL})"

        logger.info(f"Analyzer LLM respondeu em {elapsed:.1f}s via {backend_used} ({len(raw)} chars)")
        logger.debug(f"Analyzer raw response (primeiros 500 chars): {raw[:500]}")

        selections = self._parse_json(raw)
        logger.info(f"Analyzer parseou {len(selections)} temas validos de {len(raw)} chars")

        return self._selections_to_topics(selections, trends, backend_used)

    def _selections_to_topics(
        self, selections: list[dict], trends: list[TrendItem], backend_used: str
    ) -> list[AnalyzedTopic]:
        """Converte dicts parseados em AnalyzedTopic com matching de trends."""
        trend_map = {t.title.lower().strip(): t for t in trends}
        analyzed = []
        for sel in selections:
            original_title = sel.get("original_title", "")
            original_trend = trend_map.get(original_title.lower().strip())
            matched = bool(original_trend)
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
            logger.info(
                f"  Tema: '{sel['gandalf_topic']}' score={sel.get('relevance_score', 0.5):.2f} "
                f"original={'matched' if matched else 'cliche'}"
            )

        if not analyzed:
            logger.error(f"Analyzer nao produziu nenhum tema! Backend: {backend_used}")

        return analyzed

    def _parse_json(self, raw: str) -> list[dict]:
        """Parse JSON da resposta com fallbacks.

        Modelos locais (Ollama) podem retornar JSON em formatos inesperados:
        - dict wrapper: {"topics": [...]} em vez de [...]
        - lista de strings em vez de lista de dicts
        """
        data = self._try_parse(raw)

        # Se retornou dict, tratar formatos do Ollama
        if isinstance(data, dict):
            logger.debug(f"JSON retornou dict com keys: {list(data.keys())}")
            # Caso 1: dict wrapper com lista dentro ({"topics": [...]})
            for v in data.values():
                if isinstance(v, list):
                    logger.debug("Extraindo lista de dentro do dict wrapper")
                    data = v
                    break
            else:
                # Caso 2: Ollama retornou objeto unico com gandalf_topic (sem lista)
                if "gandalf_topic" in data:
                    logger.info(f"Ollama retornou objeto unico — wrapping em lista: {data.get('gandalf_topic', '?')}")
                    data = [data]
                else:
                    logger.error(f"JSON retornou dict sem lista e sem gandalf_topic: {raw[:200]}")
                    return []

        if not isinstance(data, list):
            logger.error(f"JSON nao e lista: {type(data).__name__} — {raw[:200]}")
            return []

        # Filtrar apenas dicts validos (ignorar strings, ints, etc.)
        valid = [item for item in data if isinstance(item, dict) and "gandalf_topic" in item]
        invalid_count = len(data) - len(valid)
        if invalid_count > 0:
            logger.warning(f"JSON: {invalid_count}/{len(data)} itens invalidos filtrados")
        if not valid and data:
            logger.warning(f"JSON lista sem dicts validos ({len(data)} items): {raw[:200]}")
        return valid

    def _try_parse(self, raw: str):
        """Tenta parsear JSON com multiplos fallbacks."""
        try:
            result = json.loads(raw)
            logger.debug("JSON parseado diretamente (json.loads)")
            return result
        except json.JSONDecodeError:
            pass

        if "```" in raw:
            match = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group(1))
                    logger.debug("JSON extraido de bloco markdown ```")
                    return result
                except json.JSONDecodeError:
                    pass

        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
                logger.debug("JSON extraido via regex [...]")
                return result
            except json.JSONDecodeError:
                pass

        logger.error(f"Nao foi possivel parsear JSON (nenhum fallback funcionou): {raw[:300]}")
        return []
