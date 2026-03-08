import random
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from config import (
    BACKGROUNDS_DIR,
    OUTPUT_DIR,
    COMFYUI_ENABLED,
    COMFYUI_FALLBACK_TO_STATIC,
    COMFYUI_HOST,
    COMFYUI_PORT,
    COMFYUI_TIMEOUT,
    COMFYUI_PROMPT_STRATEGY,
    COMFYUI_LORA_STRENGTH,
    COMFYUI_SAMPLING_STEPS,
    COMFYUI_GUIDANCE,
    COMFYUI_IMG2IMG_DENOISE,
    COMFYUI_REFERENCE_DIR,
    GENERATED_BACKGROUNDS_DIR,
)
from src.phrases import generate_phrases
from src.image_maker import create_image, create_placeholder_background
from src.pipeline.models import AnalyzedTopic, GeneratedContent

logger = logging.getLogger("clip-flow.generator")


class ContentGenerator:
    """Gera frases e imagens usando os módulos existentes do clip-flow."""

    def __init__(self, use_comfyui: bool | None = None):
        self.backgrounds = self._load_backgrounds()
        self._use_comfyui = use_comfyui if use_comfyui is not None else COMFYUI_ENABLED
        self._comfyui_client = None

        if self._use_comfyui:
            self._init_comfyui()

    def _load_backgrounds(self) -> list[str]:
        """Carrega imagens de fundo disponíveis."""
        extensions = ("*.jpg", "*.jpeg", "*.png", "*.webp")
        backgrounds = []
        for ext in extensions:
            backgrounds.extend(BACKGROUNDS_DIR.glob(ext))
        bg_paths = [str(p) for p in backgrounds]
        if not bg_paths:
            BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)
            placeholder = str(BACKGROUNDS_DIR / "placeholder.png")
            create_placeholder_background(placeholder)
            bg_paths = [placeholder]
        return bg_paths

    def _init_comfyui(self):
        """Inicializa cliente ComfyUI se disponivel."""
        try:
            from src.image_gen.comfyui_client import ComfyUIClient

            client = ComfyUIClient(
                host=COMFYUI_HOST,
                port=COMFYUI_PORT,
                timeout=COMFYUI_TIMEOUT,
                lora_strength=COMFYUI_LORA_STRENGTH,
                sampling_steps=COMFYUI_SAMPLING_STEPS,
                guidance=COMFYUI_GUIDANCE,
                img2img_denoise=COMFYUI_IMG2IMG_DENOISE,
            )
            if client.is_available():
                self._comfyui_client = client
                logger.info("ComfyUI conectado — geracao local de backgrounds ativada")
            else:
                logger.warning("ComfyUI nao disponivel — usando backgrounds estaticos")
                if not COMFYUI_FALLBACK_TO_STATIC:
                    raise ConnectionError("ComfyUI nao disponivel e fallback desabilitado")
        except ImportError:
            logger.warning("Modulo image_gen nao encontrado — usando backgrounds estaticos")
        except ConnectionError:
            raise
        except Exception as e:
            logger.warning(f"Erro ao inicializar ComfyUI: {e}")

    def _generate_background(self, topic: AnalyzedTopic) -> str | None:
        """Gera background via ComfyUI (img2img ou txt2img) ou retorna None."""
        if not self._comfyui_client:
            return None

        try:
            if COMFYUI_PROMPT_STRATEGY == "claude":
                from src.image_gen.prompt_builder import build_prompt_with_claude
                prompt = build_prompt_with_claude(topic)
            else:
                from src.image_gen.prompt_builder import build_prompt
                prompt = build_prompt(topic)

            GENERATED_BACKGROUNDS_DIR.mkdir(parents=True, exist_ok=True)
            output_path = str(
                GENERATED_BACKGROUNDS_DIR
                / f"mago_{int(time.time())}_{random.randint(0, 999):03d}.png"
            )

            # Tentar img2img com imagem de referencia (melhor qualidade)
            from src.image_gen.prompt_builder import select_reference_image
            ref_image = select_reference_image(topic, str(COMFYUI_REFERENCE_DIR))
            if ref_image:
                logger.info(f"Usando img2img com referencia: {Path(ref_image).name}")
                result = self._comfyui_client.generate_img2img(
                    prompt, ref_image, output_path
                )
                if result:
                    logger.info(f"Background gerado via img2img: {result}")
                    return result
                logger.warning("img2img falhou, tentando txt2img...")

            # Fallback para txt2img (LoRA)
            result = self._comfyui_client.generate_background(prompt, output_path)
            if result:
                logger.info(f"Background gerado via txt2img: {result}")
            return result

        except Exception as e:
            logger.error(f"Falha na geracao ComfyUI: {e}")
            return None

    def generate(self, topic: AnalyzedTopic, phrases_per_topic: int = 1) -> list[GeneratedContent]:
        """Gera frases e imagens para um tópico analisado."""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        results = []

        try:
            phrases = generate_phrases(topic.gandalf_topic, phrases_per_topic)
        except Exception as e:
            logger.error(f"Falha na geração de frases para '{topic.gandalf_topic}': {e}")
            return []

        for phrase in phrases:
            try:
                # Tentar gerar background via ComfyUI
                bg = self._generate_background(topic)

                # Fallback para background estatico
                if bg is None:
                    bg = random.choice(self.backgrounds)
                    logger.debug(f"Usando background estatico: {bg}")

                image_path = create_image(phrase, bg)
                content = GeneratedContent(
                    phrase=phrase,
                    image_path=image_path,
                    topic=topic.gandalf_topic,
                    source=topic.original_trend.source,
                )
                results.append(content)
                logger.info(f"Gerado: {phrase[:50]}... -> {image_path}")
            except Exception as e:
                logger.error(f"Falha na geração de imagem para '{phrase[:30]}...': {e}")

        return results
