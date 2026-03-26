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


# ---------------------------------------------------------------------------
# Phrase validation (D-15): length, language, and format checks
# ---------------------------------------------------------------------------

# Common English words that are OK in Brazilian Portuguese memes (Brazilianisms)
_ALLOWED_ENGLISH = {
    "fake", "hype", "crush", "stalker", "like", "selfie", "stories",
    "delivery", "home office", "wifi", "online", "streaming",
    "playlist", "lo-fi", "lofi", "spoiler", "meme", "trend",
    "reels", "feed", "post", "hack", "top", "vibe", "mood",
    "cringe", "ghosting", "match", "date", "ok", "sorry",
}

# Common Portuguese markers — if any appear, the text is likely PT
_PT_MARKERS = {
    "que", "nao", "com", "uma", "pra", "quando", "mas", "meu",
    "minha", "voce", "essa", "esse", "aqui", "mais", "como",
    "vai", "vou", "sou", "tem", "esta", "seu", "sua",
    "pro", "tudo", "isso", "nada", "todo", "cada",
    "ser", "ter", "ver", "dar", "por", "ate", "bem",
    "sim", "nos", "eles", "ela", "ele", "nem", "sem",
    "dia", "hoje", "vida", "mundo", "gente", "coisa",
    "muito", "sobre", "sempre", "nunca", "outro", "todos",
    "onde", "quem", "qual", "tipo", "pode", "quer", "fica",
}

# Common English-only words (unlikely in BR Portuguese informal text)
_ENGLISH_ONLY = {
    "the", "and", "you", "that", "this", "with", "for", "are",
    "but", "not", "have", "from", "they", "been", "said",
    "each", "which", "their", "will", "other", "about",
    "would", "make", "just", "know", "take", "people",
    "into", "year", "your", "good", "some", "could", "them",
    "than", "first", "long", "little", "very", "over",
    "after", "thing", "give", "most", "because", "where",
    "should", "still", "before", "here", "through", "think",
    "well", "also", "back", "only", "come", "every", "between",
    "when", "what", "there", "can", "all", "were", "her",
    "his", "one", "our", "out", "had", "has", "its",
    "then", "being", "does", "did", "get", "got", "made",
    "many", "much", "these", "those", "such", "keep",
    "never", "always", "really", "again", "look", "want",
    "right", "now", "find", "way", "may", "down", "who",
}


def _validate_phrase(phrase: str, max_chars: int = 120) -> tuple[bool, str]:
    """Validate a phrase for image overlay suitability.

    Returns (is_valid, reason). Reason is empty if valid.
    """
    # Check 1: Length
    if len(phrase) > max_chars:
        return False, f"too_long ({len(phrase)} > {max_chars})"

    if len(phrase) < 10:
        return False, f"too_short ({len(phrase)} chars)"

    # Check 2: Language — ensure it's predominantly Portuguese
    words = phrase.lower().split()
    if len(words) < 3:
        return False, "too_few_words"

    # Strategy: check for Portuguese markers AND English-only words.
    # If any non-ASCII character exists (accents), it's very likely Portuguese.
    has_non_ascii = not phrase.isascii()
    has_pt_marker = any(w in _PT_MARKERS for w in words)
    has_allowed_en = any(w in _ALLOWED_ENGLISH for w in words)

    if has_non_ascii or has_pt_marker:
        # Very likely Portuguese — pass language check
        pass
    elif has_allowed_en:
        # Has Brazilianisms (like "meme", "vibe") but no PT markers — likely PT slang
        pass
    else:
        # All ASCII, no PT markers, no Brazilianisms — likely English
        english_only_count = sum(1 for w in words if w in _ENGLISH_ONLY)
        english_ratio = english_only_count / len(words) if words else 0
        if english_ratio > 0.3:
            return False, f"too_much_english ({english_only_count}/{len(words)} words)"
        # Even without matching English keywords, no PT markers is suspicious
        if len(words) >= 5:
            return False, f"no_pt_markers (0 Portuguese markers in {len(words)} words)"

    # Check 3: Not empty/placeholder
    if phrase.strip().startswith("[") or phrase.strip().startswith("{"):
        return False, "placeholder_text"

    return True, ""


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
    phrases = [
        re.sub(r'^\d+[\.\)]\s*', '', line.strip())
        for line in raw_text.strip().splitlines()
        if line.strip()
    ]
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

                # Validate phrases (per D-15)
                max_chars = self._max_chars or 120
                validated = []
                for phrase in phrases:
                    is_valid, reason = _validate_phrase(phrase, max_chars)
                    if is_valid:
                        validated.append(phrase)
                    else:
                        logger.info(f"[{work_order.order_id}] Phrase rejected ({reason}): '{phrase[:50]}...'")

                # If too many rejected, retry once
                if len(validated) < count and len(validated) < len(phrases):
                    logger.info(f"[{work_order.order_id}] {len(phrases) - len(validated)} phrases rejected, regenerating...")
                    retry_phrases = await asyncio.to_thread(
                        _generate_with_prompt,
                        self._system_prompt,
                        work_order.gandalf_topic,
                        count - len(validated),
                        self._max_chars,
                        work_order.humor_angle,
                    )
                    for phrase in retry_phrases:
                        is_valid, reason = _validate_phrase(phrase, max_chars)
                        if is_valid:
                            validated.append(phrase)

                return validated[:count]
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

        # Validate phrases before scoring (per D-15)
        max_chars = self._max_chars or 120
        valid_phrases = []
        for phrase in all_phrases:
            is_valid, reason = _validate_phrase(phrase, max_chars)
            if is_valid:
                valid_phrases.append(phrase)
            else:
                logger.info(f"[{work_order.order_id}] A/B phrase rejected ({reason}): '{phrase[:50]}...'")

        # If too many rejected, retry once for replacements
        if len(valid_phrases) < total_to_generate and len(valid_phrases) < len(all_phrases):
            needed = total_to_generate - len(valid_phrases)
            logger.info(f"[{work_order.order_id}] A/B: {len(all_phrases) - len(valid_phrases)} rejected, regenerating {needed}...")
            async with _gemini_semaphore:
                try:
                    retry_phrases = await asyncio.to_thread(
                        _generate_with_prompt,
                        self._system_prompt,
                        work_order.gandalf_topic,
                        needed,
                        self._max_chars,
                        work_order.humor_angle,
                    )
                    for phrase in retry_phrases:
                        is_valid, reason = _validate_phrase(phrase, max_chars)
                        if is_valid:
                            valid_phrases.append(phrase)
                except Exception as e:
                    logger.warning(f"[{work_order.order_id}] A/B retry failed: {e}")

        all_phrases = valid_phrases
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
