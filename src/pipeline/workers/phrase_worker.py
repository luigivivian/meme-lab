"""PhraseWorker — gera frases via Gemini API com A/B testing opcional.

Wrapper async de src.phrases.generate_phrases().
Suporta system_prompt customizado por personagem e scoring de alternativas.
"""

import asyncio
import json
import logging
import re

from config import GEMINI_MAX_CONCURRENT, SYSTEM_PROMPT, PHRASE_AB_ENABLED, PHRASE_AB_ALTERNATIVES
from src.llm_client import generate
from src.pipeline.models_v2 import WorkOrder

logger = logging.getLogger("clip-flow.worker.phrase")

# Semaforo global para limitar chamadas simultaneas ao Gemini
_gemini_semaphore = asyncio.Semaphore(GEMINI_MAX_CONCURRENT)

# Prompt de scoring para A/B testing
_SCORING_PROMPT = """Voce e um especialista em conteudo viral para Instagram.
Avalie cada frase de 0 a 10 em tres criterios:
- viralidade: potencial de compartilhamento e engajamento
- humor: nivel de comedia e diversao
- identificacao: quanto o publico BR se identifica

Responda APENAS com JSON valido (array):
[{"frase": "...", "viralidade": N, "humor": N, "identificacao": N}]

Frases para avaliar:
"""


def _generate_with_prompt(
    system_prompt: str,
    topic: str,
    count: int,
    max_chars: int | None = None,
    humor_angle: str | None = None,
) -> list[str]:
    """Gera frases usando system_prompt customizado."""
    user_msg = f"TEMA OBRIGATORIO: {topic}\n"
    if humor_angle:
        user_msg += f"ANGULO DE HUMOR: {humor_angle}\n"
    user_msg += f"\nGere EXATAMENTE {count} frase(s) sobre o tema acima."
    user_msg += "\nATENCAO: As frases DEVEM ser sobre o tema especificado, nao sobre outros assuntos."
    if max_chars:
        user_msg += f"\nMaximo {max_chars} caracteres por frase."

    logger.debug(f"PhraseWorker prompt: {user_msg[:200]}")

    raw_text = generate(
        system_prompt=system_prompt,
        user_message=user_msg,
        max_tokens=2048,
        tier="lite",
    )
    phrases = [line.strip() for line in raw_text.strip().splitlines() if line.strip()]
    return phrases


def _score_phrases(phrases: list[str]) -> list[dict]:
    """Pontua frases via Gemini (viralidade, humor, identificacao).

    Returns:
        Lista de dicts com frase, scores individuais e score composto.
    """
    phrases_text = "\n".join(f"- {p}" for p in phrases)
    raw = generate(
        system_prompt=_SCORING_PROMPT + phrases_text,
        user_message="Avalie as frases acima.",
        max_tokens=1024,
        tier="lite",
    )

    # Extrair JSON do response (pode vir com markdown)
    json_match = re.search(r'\[.*\]', raw, re.DOTALL)
    if not json_match:
        logger.warning("Scoring retornou formato invalido, usando scores padrao")
        return [{"frase": p, "viralidade": 5, "humor": 5, "identificacao": 5} for p in phrases]

    try:
        scored = json.loads(json_match.group())
    except json.JSONDecodeError:
        logger.warning("JSON de scoring invalido, usando scores padrao")
        return [{"frase": p, "viralidade": 5, "humor": 5, "identificacao": 5} for p in phrases]

    # Calcular score composto e garantir que todas as frases tem entrada
    results = []
    for i, phrase in enumerate(phrases):
        entry = scored[i] if i < len(scored) else {}
        v = min(max(float(entry.get("viralidade", 5)), 0), 10)
        h = min(max(float(entry.get("humor", 5)), 0), 10)
        ident = min(max(float(entry.get("identificacao", 5)), 0), 10)
        score = round(v * 0.4 + h * 0.35 + ident * 0.25, 2)
        results.append({
            "frase": phrase,
            "viralidade": v,
            "humor": h,
            "identificacao": ident,
            "score": score,
        })

    return results


class PhraseWorker:
    """Gera frases humoristicas via Gemini API com A/B testing opcional."""

    def __init__(self, system_prompt: str | None = None, max_chars: int | None = None):
        self._custom_prompt = bool(system_prompt)
        self._system_prompt = system_prompt or SYSTEM_PROMPT
        self._max_chars = max_chars
        if self._custom_prompt:
            logger.info(f"PhraseWorker usando system_prompt customizado ({len(self._system_prompt)} chars)")
        else:
            logger.info("PhraseWorker usando SYSTEM_PROMPT padrao (mago-mestre)")

    async def generate(self, work_order: WorkOrder, count: int = 1) -> list[str]:
        """Gera frases para um WorkOrder (modo simples).

        Args:
            work_order: ordem de trabalho com gandalf_topic.
            count: quantidade de frases a gerar.

        Returns:
            Lista de frases geradas.
        """
        async with _gemini_semaphore:
            logger.info(
                f"[{work_order.order_id}] Gerando {count} frase(s) "
                f"para '{work_order.gandalf_topic}'"
            )
            try:
                phrases = await asyncio.to_thread(
                    _generate_with_prompt,
                    self._system_prompt,
                    work_order.gandalf_topic,
                    count,
                    self._max_chars,
                    work_order.humor_angle,
                )
                logger.info(
                    f"[{work_order.order_id}] {len(phrases)} frase(s) gerada(s)"
                )
                return phrases
            except Exception as e:
                logger.error(
                    f"[{work_order.order_id}] Falha na geracao de frases: {e}"
                )
                return []

    async def generate_with_scoring(
        self,
        work_order: WorkOrder,
        count: int = 1,
        alternatives: int = PHRASE_AB_ALTERNATIVES,
    ) -> tuple[list[str], list[dict]]:
        """Gera frases com A/B testing — gera alternativas, pontua e seleciona melhor.

        Args:
            work_order: ordem de trabalho com gandalf_topic.
            count: quantidade de frases finais desejadas.
            alternatives: quantas alternativas gerar por slot.

        Returns:
            Tupla (melhores_frases, todas_alternativas_com_scores).
        """
        # Gerar mais frases do que o necessario para ter opcoes
        total_to_generate = count * alternatives
        async with _gemini_semaphore:
            logger.info(
                f"[{work_order.order_id}] A/B: gerando {total_to_generate} alternativas "
                f"para '{work_order.gandalf_topic}'"
            )
            try:
                all_phrases = await asyncio.to_thread(
                    _generate_with_prompt,
                    self._system_prompt,
                    work_order.gandalf_topic,
                    total_to_generate,
                    self._max_chars,
                    work_order.humor_angle,
                )
            except Exception as e:
                logger.error(f"[{work_order.order_id}] A/B geracao falhou: {e}")
                return [], []

        if not all_phrases:
            return [], []

        # Pontuar todas as frases
        async with _gemini_semaphore:
            try:
                scored = await asyncio.to_thread(_score_phrases, all_phrases)
            except Exception as e:
                logger.warning(f"[{work_order.order_id}] A/B scoring falhou: {e}, usando primeira frase")
                return all_phrases[:count], []

        # Ordenar por score composto (maior primeiro)
        scored.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Selecionar as N melhores
        best_phrases = [s["frase"] for s in scored[:count]]
        logger.info(
            f"[{work_order.order_id}] A/B: melhor score={scored[0].get('score', 0)} "
            f"de {len(scored)} alternativas"
        )

        return best_phrases, scored
