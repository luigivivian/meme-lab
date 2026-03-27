"""Gemini Web Trends Agent — busca trends virais BR via Gemini + Google Search grounding.

Usa a ferramenta google_search do Gemini para buscar o que esta viral no Brasil
hoje e retornar topicos com potencial de meme — sem API key adicional.

Requer: GOOGLE_API_KEY no .env (ja usada pelo resto do projeto).

Modelo: gemini-2.0-flash (suporte nativo a google_search grounding).
"""

import asyncio
import json
import logging
import os
import re

from dotenv import load_dotenv
from google import genai
from google.genai import types

from config import GEMINI_TRENDS_MAX_TOPICS, GEMINI_TRENDS_MODEL
from src.pipeline.agents.async_base import AsyncSourceAgent
from src.pipeline.models_v2 import TrendEvent, TrendSource

load_dotenv()

logger = logging.getLogger("clip-flow.agent.gemini_web_trends")

_SYSTEM_PROMPT = """Voce e um analista de tendencias digitais especializado em cultura brasileira e memes.
Sua tarefa: pesquisar o que esta viral no Brasil agora e identificar topicos com alto potencial de meme.

CRITERIOS para selecionar topicos:
- Situacoes cotidianas engraçadas e relatable (trabalho, relacionamentos, familia, dinheiro)
- Trends do TikTok BR, Twitter BR, Instagram Reels BR
- Expressoes e gírias novas circulando na internet brasileira
- Memes de comportamento humano universal (mas com sotaque BR)
- Humor sobre tecnologia, redes sociais, series/filmes em alta
- Piadas sobre segunda-feira, fim do mes, calor, transito, precos

NUNCA incluir: politica partidaria seria, tragedias, crimes, conteudo ofensivo, religiao.

Responda SOMENTE com um array JSON valido, sem markdown, sem texto extra:
[
  {"titulo": "topico viral aqui", "categoria": "cotidiano|tecnologia|humor|entretenimento|comportamento", "score": 0.0}
]

O score deve ser entre 0.0 e 1.0 indicando potencial de meme (1.0 = meme perfeito).
"""

_USER_PROMPT = (
    f"Pesquise o que esta viral e sendo mais compartilhado no Brasil HOJE. "
    f"Foque em memes, situacoes engraçadas e trends de humor. "
    f"Retorne exatamente {GEMINI_TRENDS_MAX_TOPICS} topicos no formato JSON especificado. "
    f"Use sua busca para encontrar informacoes ATUAIS de hoje."
)

# Regex para extrair JSON array da resposta (caso venha com texto extra)
_JSON_RE = re.compile(r"\[.*?\]", re.DOTALL)


def _parse_topics(raw: str) -> list[dict]:
    """Extrai e parseia lista de topicos do texto da resposta."""
    # Tenta parse direto
    text = raw.strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # Tenta extrair array JSON via regex
    match = _JSON_RE.search(text)
    if match:
        try:
            data = json.loads(match.group())
            if isinstance(data, list):
                return data
        except json.JSONDecodeError:
            pass

    return []


def _extract_text(response) -> str:
    """Extrai texto limpo da resposta Gemini (ignora thinking tokens)."""
    try:
        parts = response.candidates[0].content.parts
        text_parts = [p.text for p in parts if p.text and not getattr(p, "thought", False)]
        if text_parts:
            return "".join(text_parts)
    except (AttributeError, IndexError):
        pass
    return getattr(response, "text", "") or ""


class GeminiWebTrendsAgent(AsyncSourceAgent):
    """Descobre trends virais do Brasil via Gemini com Google Search grounding."""

    def __init__(self):
        super().__init__("gemini_web_trends")
        self._api_key = os.getenv("GOOGLE_API_KEY", "")
        self._client: genai.Client | None = None

    def _get_client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(api_key=self._api_key)
        return self._client

    async def fetch(self) -> list[TrendEvent]:
        try:
            events = await asyncio.to_thread(self._fetch_grounded)
            self.logger.info(f"Gemini Web Trends: {len(events)} topicos coletados")
            return events
        except Exception as e:
            self.logger.error(f"Gemini Web Trends falhou: {e}")
            return []

    def _fetch_grounded(self) -> list[TrendEvent]:
        client = self._get_client()
        response = client.models.generate_content(
            model=GEMINI_TRENDS_MODEL,
            contents=_USER_PROMPT,
            config=types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.4,
                max_output_tokens=2048,
            ),
        )

        raw_text = _extract_text(response)
        if not raw_text:
            self.logger.warning("Gemini Web Trends: resposta vazia")
            return []

        topics = _parse_topics(raw_text)
        if not topics:
            self.logger.warning(
                f"Gemini Web Trends: nao foi possivel parsear JSON. "
                f"Resposta (primeiros 200 chars): {raw_text[:200]}"
            )
            return []

        events: list[TrendEvent] = []
        for item in topics:
            titulo = str(item.get("titulo", "")).strip()
            if not titulo or len(titulo) < 3:
                continue
            categoria = str(item.get("categoria", "humor")).strip()
            score_raw = item.get("score", 0.75)
            try:
                score = max(0.0, min(1.0, float(score_raw)))
            except (ValueError, TypeError):
                score = 0.75

            events.append(
                TrendEvent(
                    title=titulo,
                    source=TrendSource.GEMINI_TRENDS,
                    score=score,
                    category=categoria,
                    metadata={"grounded": True, "model": GEMINI_TRENDS_MODEL},
                )
            )

        return events

    async def is_available(self) -> bool:
        return bool(self._api_key)
