"""LLM Client — camada de abstracao para chamadas de LLM.

Usa Google Gemini (SDK google-genai) como provider padrao.
Trocar de provider = alterar apenas este arquivo.
"""

import asyncio
import logging
import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger("clip-flow.llm")

# API key
_api_key = os.getenv("GOOGLE_API_KEY", "")

# Cliente global (inicializado lazy)
_client: genai.Client | None = None


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


def _model_name(model_name: str | None = None) -> str:
    """Retorna nome do modelo."""
    return model_name or os.getenv("GEMINI_MODEL", "gemini-2.0-flash")


def generate(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 1024,
    model_name: str | None = None,
) -> str:
    """Gera texto via Gemini (sincrono).

    Args:
        system_prompt: instrucoes de sistema
        user_message: mensagem do usuario
        max_tokens: limite de tokens na resposta
        model_name: modelo Gemini (default: GEMINI_MODEL env ou gemini-2.0-flash)

    Returns:
        texto gerado
    """
    client = _get_client()
    response = client.models.generate_content(
        model=_model_name(model_name),
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
            temperature=0.9,
        ),
    )
    return response.text


async def agenerate(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 1024,
    model_name: str | None = None,
    semaphore: asyncio.Semaphore | None = None,
) -> str:
    """Gera texto via Gemini (async via thread).

    Args:
        system_prompt: instrucoes de sistema
        user_message: mensagem do usuario
        max_tokens: limite de tokens na resposta
        model_name: modelo Gemini
        semaphore: semaforo para rate limiting

    Returns:
        texto gerado
    """
    async def _call():
        return await asyncio.to_thread(
            generate, system_prompt, user_message, max_tokens, model_name
        )

    if semaphore:
        async with semaphore:
            return await _call()
    return await _call()


def generate_json(
    system_prompt: str,
    user_message: str,
    max_tokens: int = 2048,
    model_name: str | None = None,
) -> str:
    """Gera JSON via Gemini com response_mime_type.

    Retorna string JSON (caller faz o parse).
    """
    client = _get_client()
    response = client.models.generate_content(
        model=_model_name(model_name),
        contents=user_message,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            max_output_tokens=max_tokens,
            temperature=0.7,
            response_mime_type="application/json",
        ),
    )
    return response.text
