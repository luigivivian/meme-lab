"""CaptionWorker — gera legenda Instagram com CTA via Gemini.

Cria legendas engajantes que complementam a frase do personagem,
com chamada para acao (salvar, compartilhar, marcar amigos).
"""

import asyncio
import logging

from config import GEMINI_MAX_CONCURRENT, CAPTION_MAX_LENGTH
from src.pipeline.models_v2 import ContentPackage
from src.llm_client import generate

logger = logging.getLogger("clip-flow.worker.caption")

# Reutiliza semaforo global do Gemini
_gemini_semaphore = asyncio.Semaphore(GEMINI_MAX_CONCURRENT)

# Prompt padrao (mago-mestre) — usado quando personagem nao tem caption_prompt
_DEFAULT_CAPTION_PROMPT = """Voce e o social media manager do perfil @magomestre420 no Instagram.
O perfil publica memes com frases engracadas de um mago sabio e zoeiro.

Crie uma legenda para Instagram que:
1. Complementa a frase do personagem (nao repita a frase, ela ja esta na imagem)
2. Seja curta, engajante e gere interacao
3. Inclua uma CTA natural (salvar, compartilhar, marcar amigo)
4. Use no maximo 3 emojis relevantes
5. NAO use hashtags (serao adicionadas separadamente)
6. Maximo {max_length} caracteres

Tom: leve, zoeiro, relatable. Como se fosse um post de meme viral.

Exemplos de CTA bons:
- "Marca aquele amigo que e assim"
- "Salva pra mandar no grupo"
- "Se voce nao se identificou, voce esta mentindo"

Responda APENAS com a legenda, sem aspas ou formatacao extra."""

# Template generico para personagens com handle customizado
_CHARACTER_CAPTION_TEMPLATE = """Voce e o social media manager do perfil {handle} no Instagram.
{character_description}

Crie uma legenda para Instagram que:
1. Complementa a frase do personagem (nao repita a frase, ela ja esta na imagem)
2. Seja curta, engajante e gere interacao
3. Inclua uma CTA natural (salvar, compartilhar, marcar amigo)
4. Use no maximo 3 emojis relevantes
5. NAO use hashtags (serao adicionadas separadamente)
6. Maximo {max_length} caracteres

Tom: leve, zoeiro, relatable. Como se fosse um post de meme viral.

Exemplos de CTA bons:
- "Marca aquele amigo que e assim"
- "Salva pra mandar no grupo"
- "Se voce nao se identificou, voce esta mentindo"

Responda APENAS com a legenda, sem aspas ou formatacao extra."""


class CaptionWorker:
    """Gera legenda Instagram com CTA via Gemini API."""

    def __init__(
        self,
        character_name: str | None = None,
        character_handle: str | None = None,
        caption_prompt: str | None = None,
    ):
        self._character_name = character_name
        self._character_handle = character_handle
        self._caption_prompt = caption_prompt
        if caption_prompt:
            logger.info(f"CaptionWorker usando caption_prompt customizado ({len(caption_prompt)} chars)")
        elif character_handle:
            logger.info(f"CaptionWorker usando template para {character_handle}")
        else:
            logger.info("CaptionWorker usando prompt padrao (mago-mestre)")

    def _build_prompt(self) -> str:
        """Constroi prompt de caption baseado no personagem."""
        # Prioridade: caption_prompt customizado > template com handle > default
        if self._caption_prompt:
            prompt = self._caption_prompt
            if "{max_length}" in prompt:
                prompt = prompt.format(max_length=CAPTION_MAX_LENGTH)
            return prompt
        if self._character_handle:
            desc = f"O perfil publica memes com frases engracadas de {self._character_name or 'um personagem'}."
            return _CHARACTER_CAPTION_TEMPLATE.format(
                handle=self._character_handle,
                character_description=desc,
                max_length=CAPTION_MAX_LENGTH,
            )
        return _DEFAULT_CAPTION_PROMPT.format(max_length=CAPTION_MAX_LENGTH)

    async def generate(self, package: ContentPackage) -> str:
        """Gera legenda para um ContentPackage.

        Returns:
            legenda formatada ou string vazia se falhar
        """
        async with _gemini_semaphore:
            try:
                caption = await asyncio.to_thread(self._generate_sync, package)
                logger.info(f"Legenda gerada ({len(caption)} chars)")
                return caption
            except Exception as e:
                logger.error(f"Falha na geracao de legenda: {e}")
                return ""

    def _generate_sync(self, package: ContentPackage) -> str:
        """Geracao sincrona de legenda via Gemini."""
        prompt = self._build_prompt()

        humor_angle = ""
        if package.work_order:
            humor_angle = f"\nAngulo de humor: {package.work_order.humor_angle}"

        text = generate(
            system_prompt=prompt,
            user_message=(
                f"Frase na imagem: \"{package.phrase}\"\n"
                f"Tema: {package.topic}"
                f"{humor_angle}"
            ),
            max_tokens=512,
            tier="lite",
        )
        return text.strip()
