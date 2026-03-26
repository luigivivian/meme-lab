"""LLM Client — camada de abstracao para chamadas de LLM.

Suporta dois backends:
- **Gemini** (padrao): Google Gemini API via google-genai SDK
- **Ollama** (local): modelos locais via Ollama HTTP API (custo zero)

Backend controlado por config.LLM_BACKEND ("gemini" | "ollama").
Fallback automatico: se Ollama falhar, tenta Gemini Flash Lite.
"""

import asyncio
import json
import logging
import os

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger("clip-flow.llm")

# API key Gemini
_api_key = os.getenv("GOOGLE_API_KEY", "")

# Cliente Gemini global (inicializado lazy)
_client: genai.Client | None = None

# Cliente httpx global para Ollama (inicializado lazy)
_ollama_client: httpx.Client | None = None


def _get_client() -> genai.Client:
    """Retorna cliente Gemini (singleton)."""
    global _client
    if not _api_key:
        raise ValueError(
            "GOOGLE_API_KEY nao configurada. "
            "Obtenha sua chave em: https://aistudio.google.com/apikey"
        )
    if _client is None:
        _client = genai.Client(api_key=_api_key)
    return _client


def _get_ollama_client() -> httpx.Client:
    """Retorna cliente HTTP para Ollama (singleton)."""
    global _ollama_client
    from config import OLLAMA_HOST, OLLAMA_TIMEOUT
    if _ollama_client is None:
        _ollama_client = httpx.Client(
            base_url=OLLAMA_HOST,
            timeout=OLLAMA_TIMEOUT,
        )
    return _ollama_client


def _should_use_ollama() -> bool:
    """Verifica se deve usar Ollama como backend."""
    from config import LLM_BACKEND
    return LLM_BACKEND == "ollama"


def _ollama_available() -> bool:
    """Verifica se servidor Ollama esta respondendo."""
    try:
        client = _get_ollama_client()
        resp = client.get("/api/tags")
        return resp.status_code == 200
    except Exception:
        return False


def _generate_ollama(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 1024,
    temperature: float = 0.9,
    json_mode: bool = False,
) -> str:
    """Gera texto via Ollama HTTP API.

    Args:
        system_prompt: instrucoes de sistema
        user_message: mensagem do usuario
        max_tokens: num_predict (limite de tokens)
        temperature: temperatura de amostragem
        json_mode: se True, forca resposta JSON

    Returns:
        texto gerado
    """
    from config import OLLAMA_MODEL
    client = _get_ollama_client()

    payload = {
        "model": OLLAMA_MODEL,
        "system": system_prompt,
        "prompt": user_message,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
        },
    }
    if json_mode:
        payload["format"] = "json"

    logger.info(f"Ollama chamando {OLLAMA_MODEL} (json_mode={json_mode}, max_tokens={max_tokens})...")
    resp = client.post("/api/generate", json=payload)
    resp.raise_for_status()
    data = resp.json()
    text = data.get("response", "")

    eval_count = data.get("eval_count", "?")
    total_ns = data.get("total_duration", 0)
    elapsed_s = total_ns / 1e9 if total_ns else 0
    logger.info(
        f"Ollama respondeu em {elapsed_s:.1f}s — model={OLLAMA_MODEL}, "
        f"eval_count={eval_count}, response_len={len(text)} chars"
    )
    if json_mode:
        logger.debug(f"Ollama JSON response (primeiros 500 chars): {text[:500]}")

    if not text.strip():
        logger.warning(f"Ollama retornou resposta vazia! model={OLLAMA_MODEL}")

    return text


def _model_name(model_name: str | None = None, tier: str = "normal") -> str:
    """Retorna nome do modelo Gemini baseado no tier de custo.

    Args:
        model_name: override explicito (ignora tier)
        tier: "lite" para Flash Lite ($0.40/1M), "normal" para Flash ($2.50/1M)
    """
    if model_name:
        return model_name
    from config import GEMINI_MODEL_LITE, GEMINI_MODEL_NORMAL, COST_MODE
    # Em modo eco, tudo vira lite
    if COST_MODE == "eco":
        return GEMINI_MODEL_LITE
    if tier == "lite":
        return GEMINI_MODEL_LITE
    return GEMINI_MODEL_NORMAL


def _generate_gemini(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 1024,
    model_name: str | None = None,
    tier: str = "normal",
) -> str:
    """Gera texto via Gemini API."""
    model = _model_name(model_name, tier=tier)
    client = _get_client()
    response = client.models.generate_content(
        model=model,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
            temperature=0.9,
        ),
    )
    logger.debug(f"Gemini call: model={model}, tier={tier}, tokens={max_tokens}")
    return _extract_text(response)


def generate(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 1024,
    model_name: str | None = None,
    tier: str = "normal",
) -> str:
    """Gera texto via LLM (sincrono).

    Usa Ollama se configurado (LLM_BACKEND=ollama), com fallback para Gemini.
    Se model_name for fornecido, forca Gemini (modelo especifico).

    Args:
        system_prompt: instrucoes de sistema
        user_message: mensagem do usuario
        max_tokens: limite de tokens na resposta
        model_name: override de modelo Gemini (ignora Ollama)
        tier: "lite" para chamadas baratas, "normal" para qualidade

    Returns:
        texto gerado
    """
    # Se model_name especifico, sempre usa Gemini
    if not model_name and _should_use_ollama():
        try:
            return _generate_ollama(system_prompt, user_message, max_tokens)
        except Exception as e:
            from config import OLLAMA_FALLBACK_TO_GEMINI
            if OLLAMA_FALLBACK_TO_GEMINI:
                logger.warning(f"Ollama falhou ({e}), fallback para Gemini Flash Lite")
                return _generate_gemini(system_prompt, user_message, max_tokens, tier="lite")
            raise

    return _generate_gemini(system_prompt, user_message, max_tokens, model_name, tier)


async def agenerate(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 1024,
    model_name: str | None = None,
    semaphore: asyncio.Semaphore | None = None,
    tier: str = "normal",
) -> str:
    """Gera texto via Gemini (async via thread).

    Args:
        system_prompt: instrucoes de sistema
        user_message: mensagem do usuario
        max_tokens: limite de tokens na resposta
        model_name: override de modelo
        semaphore: semaforo para rate limiting
        tier: "lite" para chamadas baratas, "normal" para qualidade

    Returns:
        texto gerado
    """
    async def _call():
        return await asyncio.to_thread(
            generate, system_prompt, user_message, max_tokens, model_name, tier
        )

    if semaphore:
        async with semaphore:
            return await _call()
    return await _call()


def _extract_text(response) -> str:
    """Extrai apenas texto do modelo, ignorando thinking tokens (gemini-2.5+)."""
    try:
        parts = response.candidates[0].content.parts
        text_parts = [p.text for p in parts if p.text and not getattr(p, "thought", False)]
        if text_parts:
            return "".join(text_parts)
    except (AttributeError, IndexError):
        pass
    return response.text or ""


def generate_json(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 4096,
    model_name: str | None = None,
    tier: str = "normal",
) -> str:
    """Gera JSON via LLM.

    Retorna string JSON (caller faz o parse).
    Ollama usa format="json", Gemini usa response_mime_type.
    """
    # Ollama com json_mode
    if not model_name and _should_use_ollama():
        try:
            return _generate_ollama(
                system_prompt, user_message, max_tokens,
                temperature=0.7, json_mode=True,
            )
        except Exception as e:
            from config import OLLAMA_FALLBACK_TO_GEMINI
            if OLLAMA_FALLBACK_TO_GEMINI:
                logger.warning(f"Ollama JSON falhou ({e}), fallback para Gemini")
            else:
                raise

    # Gemini com response_mime_type
    model = _model_name(model_name, tier=tier)
    client = _get_client()
    response = client.models.generate_content(
        model=model,
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
            temperature=0.7,
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    logger.debug(f"Gemini JSON call: model={model}, tier={tier}, tokens={max_tokens}")
    return _extract_text(response)
