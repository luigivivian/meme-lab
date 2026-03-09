"""GeminiImageClient — geracao de imagens do Mago via Gemini API.

Pipeline Nano Banana: geracao com referencias visuais + refinamento iterativo.
Extrai a logica do notebook Colab (mago_api_server) em modulo reutilizavel.
"""

import asyncio
import logging
import random
import time
from datetime import datetime
from io import BytesIO
from pathlib import Path

import PIL.Image

from src.llm_client import _get_client
from src.image_gen.prompt_builder import KEYWORD_MAP

logger = logging.getLogger("clip-flow.gemini_image")

# Modelos em ordem de preferencia (Nano Banana Pipeline)
MODELOS_IMAGEM = [
    "gemini-2.5-flash-image",
    "gemini-2.0-flash-exp-image-generation",
    "gemini-3.1-flash-image-preview",
    "gemini-3-pro-image-preview",
]

# DNA do personagem — fotorrealista cinematico (Gandalf o Cinzento)
CHARACTER_DNA = """Photorealistic fantasy portrait of an ancient wise wizard with the following EXACT traits (NEVER change):

FACE & SKIN:
- Approximately 90 years old, deeply wrinkled weathered skin with natural skin pores
- Prominent aquiline nose, thick bushy silver-grey eyebrows
- Piercing intense pale blue-grey eyes with depth, wisdom, and subtle moisture reflection
- Weathered smile lines, age spots on temples, hyper realistic skin texture

BEARD & HAIR:
- Very long flowing silver-white beard reaching chest, slightly unkempt natural texture
- Individual hair strands visible, natural grey-white gradients (NEVER short or neat)
- Wispy silver hair visible under hat brim

HAT:
- Wide-brimmed tall pointed grey felt hat, aged and slightly bent at tip
- Weathered fabric texture, subtle dust and wear marks (NEVER remove, NEVER clean/new looking)

ROBES & CLOTHING:
- Weathered charcoal-grey wool robes with natural fabric folds and weight
- Dark midnight blue outer layer (#1A1A3E) with worn leather belt and aged brass buckle
- Subtle silver-gold thread embroidery on edges, slightly frayed
- Worn brown leather boots with creases and dust

STAFF:
- Massive gnarled wooden staff of dark twisted oak (#3E2723)
- Ancient runes barely visible carved into wood grain
- Faint warm ember-golden glow at the top (#FFD54F), like dying embers

PHYSIQUE:
- Tall, lean, slightly hunched posture conveying age and wisdom
- Large weathered hands with visible veins and knuckles

RENDERING STYLE:
- Photorealistic cinematic portrait, 85mm lens f/1.8 equivalent
- Natural subsurface skin scattering, cinematic color grading
- Subtle film grain, studio-quality lighting
- Hyper realistic fabric textures, 8K detail level
- NO cartoon, NO cel-shading, NO flat colors, NO stylization

COLOR PALETTE (strict reference):
Beard/Hair: #E8E8F0 (silver-white) | Hat: #4A5568 (weathered grey) |
Robes: #1A1A3E (dark midnight blue) | Gold details: #C8A84E (aged brass) |
Staff: #3E2723 (dark oak) | Staff glow: #FFD54F (warm ember) | Eyes: #8FA8C8 (pale blue-grey)"""

COMPOSITION = """Vertical 4:5 aspect ratio (1080x1350 pixels).
Character positioned in lower two-thirds of frame — lower third preferred.
Upper 35-40% of image open and clear for text overlay.
Shallow depth of field on background, f/1.8 bokeh effect.
Soft dramatic side lighting, cinematic color grading.
Dark atmospheric fantasy setting with warm golden accent rim lighting.
Camera angle: slight low angle, eye-level to mid-chest framing."""

NEGATIVE_TRAITS = (
    "NOT cartoon, NOT cel-shading, NOT flat colors, NOT anime/manga, NOT chibi, "
    "NOT stylized, NOT illustration, NOT watercolor, NOT oil painting brush strokes visible, "
    "NOT young wizard, NOT clean/new clothing, NOT bright saturated colors, "
    "NOT centered in frame, NOT bright white background, NOT without hat, NOT short beard, "
    "NOT threatening expression, NOT different colored robes, "
    "ABSOLUTELY NO TEXT, NO LETTERS, NO WORDS, NO CAPTIONS, NO WATERMARKS, NO TYPOGRAPHY in the image. "
    "The image must contain ZERO written text of any kind. "
    "photorealism only, no stylization whatsoever"
)

# 13 situacoes pre-definidas
SITUACOES = {
    "sabedoria": {
        "label": "Sabedoria / Conselho",
        "acao": "gentle knowing smile, one eyebrow raised wisely, leaning slightly on staff, free hand gesturing as if explaining something obvious",
        "cenario": "misty medieval forest with soft golden light filtering through ancient trees, dark moody atmosphere",
    },
    "confusao": {
        "label": "Confuso / Perplexo",
        "acao": "confused bewildered expression, head tilted to one side, one hand scratching long white beard, squinting eyes, floating question marks",
        "cenario": "dark medieval wizard study with floating books and magical scrolls, warm candlelight",
    },
    "segunda_feira": {
        "label": "Segunda-feira / Cansado",
        "acao": "extremely tired expression, heavy eyelids, hat drooping forward, holding enormous steaming coffee goblet with both hands, dark circles under eyes",
        "cenario": "early morning misty medieval kitchen, dawn light through stone window, cold blue atmosphere",
    },
    "vitoria": {
        "label": "Vitoria / Celebracao",
        "acao": "triumphant joyful expression, staff raised high with golden magical particles erupting, hat slightly flying off, robes billowing dramatically, arms wide open",
        "cenario": "epic medieval castle courtyard at sunset, dramatic golden light, magical sparkles everywhere",
    },
    "tecnologia": {
        "label": "Tecnologia / WiFi",
        "acao": "surprised amused expression, holding glowing crystal ball like a smartphone, hat askew from leaning forward, floating digital glowing runes around device",
        "cenario": "anachronistic medieval office desk with candles and ancient books, blue glow from magical screen",
    },
    "cafe": {
        "label": "Cafe / Manha",
        "acao": "content pleased expression, holding ornate ceramic mug with both hands, eyes slightly closed in pleasure, golden steam rising with magical sparkles",
        "cenario": "cozy medieval kitchen corner, warm fireplace glow, morning light",
    },
    "comida": {
        "label": "Comida / Culinaria",
        "acao": "focused proud expression, stirring large bubbling cauldron with wooden ladle, small apron over robes, floating magical ingredients, colorful vapors",
        "cenario": "magical medieval stone kitchen, warm firelight from below cauldron, herbs and potions on shelves",
    },
    "trabalho": {
        "label": "Trabalho / Escritorio",
        "acao": "concentrated serious expression, sitting at wooden desk writing on parchment scroll, multiple scrolls and books open around, quill pen in hand",
        "cenario": "dark medieval scriptorium, warm golden candlelight on desk, bookshelves reaching ceiling",
    },
    "relaxando": {
        "label": "Relaxando / Feriado",
        "acao": "blissfully asleep expression, sitting in comfortable wooden chair, hat tipped over eyes, hands folded on belly, staff leaning against wall, soft snoring aura",
        "cenario": "cozy medieval tavern corner, warm fireplace, afternoon golden light, peaceful atmosphere",
    },
    "meditando": {
        "label": "Meditando / Zen",
        "acao": "eyes closed, serene peaceful smile, sitting cross-legged on floating magical stone, staff hovering beside him, subtle ethereal blue-gold aura radiating outward",
        "cenario": "mystical mountain peak at twilight, northern lights aurora in purple-blue sky, floating clouds below",
    },
    "relacionamento": {
        "label": "Relacionamento / Romance",
        "acao": "gentle warm knowing smile, holding glowing pink heart-shaped crystal in both hands, eyes twinkling with warmth, soft magical pink and blue aura",
        "cenario": "moonlit enchanted garden with glowing flowers and fireflies, romantic soft atmosphere",
    },
    "confronto": {
        "label": "Confronto / Voce Nao Passa",
        "acao": "stern but comically determined expression, staff raised high with intense golden magical energy, one hand extended forward in firm STOP gesture, dramatic magical wind blowing robes",
        "cenario": "narrow ancient stone bridge over deep misty abyss, dramatic stormy sky, lightning in background",
    },
    "surpresa": {
        "label": "Surpreso / Espantado",
        "acao": "wide eyes of genuine shock, mouth open in surprise, both hands raised, hat blown slightly back by surprise, staff dropped sideways, exclamation sparks",
        "cenario": "dark medieval hall with dramatic revelation lighting, magical smoke and mirrors",
    },
}

# Ordem de prioridade das referencias
_REFERENCIA_PRIORIDADE = [
    "grey_wizard_front_pose_1",
    "grey_wizard_portrait_1",
    "grey_wizard_staff_raised_1",
    "grey_wizard_spell_gesture_1",
    "mago_mestre_meditando_1",
    "mago_mestre_tomando_cafe_1",
    "mago_mestre_lendo_grimorio_1",
    "mago_mestre_invocando_criatura_1",
    "mago_mestre_cozinhando_pocao_1",
    "grey_wizard_casting_magic_1",
]

# Modelo texto para AI Theme Generator
THEME_GEN_MODEL = "gemini-2.5-flash"


def _redimensionar(img: PIL.Image.Image, max_size: int = 1024) -> PIL.Image.Image:
    w, h = img.size
    if max(w, h) <= max_size:
        return img
    ratio = max_size / max(w, h)
    return img.resize((int(w * ratio), int(h * ratio)), PIL.Image.LANCZOS)


def _selecionar_referencias(
    referencias: dict[str, PIL.Image.Image], n: int = 5
) -> list[PIL.Image.Image]:
    selecionadas = []
    for nome_base in _REFERENCIA_PRIORIDADE:
        if len(selecionadas) >= n:
            break
        for nome_arquivo, img in referencias.items():
            stem = Path(nome_arquivo).stem
            if nome_base in stem and img not in selecionadas:
                selecionadas.append(img)
                break
    restantes = [img for img in referencias.values() if img not in selecionadas]
    random.shuffle(restantes)
    selecionadas.extend(restantes[: n - len(selecionadas)])
    return selecionadas[:n]


def _pil_para_part(img: PIL.Image.Image):
    """Converte PIL.Image para Part do Gemini (inline bytes)."""
    from google.genai import types

    img_r = _redimensionar(img, 1024)
    buf = BytesIO()
    img_r.save(buf, format="JPEG", quality=90)
    return types.Part.from_bytes(data=buf.getvalue(), mime_type="image/jpeg")


def _mapear_situacao(topic: str, humor_angle: str = "") -> str:
    """Mapeia topico + humor_angle para uma chave de situacao."""
    combined = f"{topic} {humor_angle}".lower()
    for keyword, scene_key in KEYWORD_MAP.items():
        if keyword in combined:
            return scene_key
    return "sabedoria"


def construir_prompt_completo(
    situacao_key: str,
    descricao_custom: str = "",
    cenario_custom: str = "",
    phrase_context: str = "",
) -> str:
    """Constroi prompt completo para geracao de imagem.

    Args:
        situacao_key: chave da situacao base (ex: "cafe", "tecnologia")
        descricao_custom: acao/pose customizada (sobrescreve a da situacao)
        cenario_custom: cenario customizado (sobrescreve o da situacao)
        phrase_context: frase que sera sobreposta na imagem — quando fornecida,
            o Gemini adapta pose/expressao/cenario para refletir o conteudo da frase,
            mantendo a situacao base como ponto de partida.
    """
    if situacao_key == "custom" or situacao_key not in SITUACOES:
        acao = descricao_custom or "standing pose holding staff, wise expression"
        cenario = cenario_custom or "dark moody medieval forest with golden atmospheric lighting"
    else:
        sit = SITUACOES[situacao_key]
        acao = descricao_custom or sit["acao"]
        cenario = cenario_custom or sit["cenario"]

    phrase_block = ""
    if phrase_context:
        phrase_block = (
            f"\nPHRASE CONTEXT (for mood/atmosphere reference ONLY — DO NOT render this text in the image):\n"
            f'"{phrase_context}"\n'
            f"CRITICAL: Do NOT write, render, or include ANY text, letters, words, or captions "
            f"in the generated image. The phrase above is ONLY for understanding the mood. "
            f"Adapt the wizard's expression, body language, pose, and scene "
            f"atmosphere to visually reflect the MOOD and MEANING of the phrase. "
            f"The background scene should feel like a natural visual companion to the text. "
            f"Use the ACTION/POSE and SETTING below as a starting point, but feel free to "
            f"adjust details (props, expressions, ambient elements) to better match the phrase.\n"
        )

    return (
        f"Generate a PHOTOREALISTIC cinematic portrait of this wizard character "
        f"matching the reference images EXACTLY.\n\n"
        f"CHARACTER (replicate precisely from reference):\n{CHARACTER_DNA}\n\n"
        f"{phrase_block}\n"
        f"ACTION/POSE:\n{acao}\n\n"
        f"SETTING/BACKGROUND:\n{cenario}\n\n"
        f"COMPOSITION:\n{COMPOSITION}\n\n"
        f"IMPORTANT — DO NOT:\n{NEGATIVE_TRAITS}\n\n"
        f"RENDERING MANDATE: This must look like a photograph or VFX still, "
        f"NOT a painting or illustration.\n"
        f"Natural skin pores, wrinkles, realistic fabric folds, cinematic shadows, "
        f"shallow DOF bokeh.\n\n"
        f"The character must look IDENTICAL to the reference images in features, "
        f"colors, and proportions.\n"
        f"Only the pose, expression, action, and background should change."
    )


class GeminiImageClient:
    """Gera imagens do Mago Mestre via Gemini API com referencias visuais.

    Suporta Pipeline Nano Banana: geracao + refinamento iterativo.
    """

    def __init__(
        self,
        reference_dir: str | Path | None = None,
        output_dir: str | Path | None = None,
        n_referencias: int = 5,
        temperatura: float = 0.85,
        max_retries_429: int = 2,
        wait_base_429: int = 60,
    ):
        from config import COMFYUI_REFERENCE_DIR, GENERATED_BACKGROUNDS_DIR

        self.reference_dir = Path(reference_dir or COMFYUI_REFERENCE_DIR)
        self.output_dir = Path(output_dir or GENERATED_BACKGROUNDS_DIR)
        self.n_referencias = n_referencias
        self.temperatura = temperatura
        self.max_retries_429 = max_retries_429
        self.wait_base_429 = wait_base_429
        self._referencias: dict[str, PIL.Image.Image] = {}
        self._loaded = False

    def _load_referencias(self) -> None:
        """Carrega imagens de referencia do disco (lazy)."""
        if self._loaded:
            return

        if not self.reference_dir.exists():
            logger.warning(f"Diretorio de referencias nao encontrado: {self.reference_dir}")
            self._loaded = True
            return

        extensoes = [".png", ".jpg", ".jpeg", ".webp"]
        for ext in extensoes:
            for img_path in sorted(self.reference_dir.glob(f"*{ext}")):
                try:
                    img = PIL.Image.open(img_path).convert("RGB")
                    self._referencias[img_path.name] = img
                except Exception as e:
                    logger.warning(f"Erro ao carregar referencia {img_path.name}: {e}")

        self._loaded = True
        logger.info(f"Carregadas {len(self._referencias)} imagens de referencia")

    def is_available(self) -> bool:
        """Verifica se o client tem referencias e API key configurada."""
        try:
            _get_client()
            self._load_referencias()
            return len(self._referencias) > 0
        except Exception:
            return False

    def _tentar_gerar(self, modelo: str, partes: list, temperatura: float) -> PIL.Image.Image | None:
        """Tenta gerar imagem com um modelo. Retorna PIL.Image ou None."""
        from google.genai import types

        client = _get_client()
        response = client.models.generate_content(
            model=modelo,
            contents=partes,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
                temperature=temperatura,
                image_config=types.ImageConfig(aspect_ratio="4:5"),
            ),
        )
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                return PIL.Image.open(BytesIO(part.inline_data.data))
        return None

    def _tentar_modelos(self, partes: list, temperatura: float) -> PIL.Image.Image | None:
        """Tenta todos os modelos em ordem com retry para 429."""
        for modelo in MODELOS_IMAGEM:
            for tentativa in range(self.max_retries_429):
                try:
                    imagem = self._tentar_gerar(modelo, partes, temperatura)
                    if imagem is None:
                        logger.warning(f"{modelo}: resposta sem imagem")
                        break
                    logger.info(f"{modelo} -> {imagem.size[0]}x{imagem.size[1]}")
                    return imagem
                except Exception as e:
                    msg = str(e)
                    if "404" in msg or "NOT_FOUND" in msg:
                        logger.warning(f"{modelo}: nao disponivel (404)")
                        break
                    elif "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                        espera = self.wait_base_429 * (2 ** tentativa)
                        logger.warning(f"{modelo}: 429, aguardando {espera}s")
                        time.sleep(espera)
                        break
                    else:
                        logger.error(f"{modelo}: {type(e).__name__}: {msg[:140]}")
                        break
        return None

    def _salvar(self, imagem: PIL.Image.Image, nome: str) -> str:
        """Salva imagem e retorna caminho."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        caminho = self.output_dir / f"{nome}.png"
        imagem.save(caminho, "PNG")
        return str(caminho)

    def generate_image(
        self,
        situacao_key: str = "sabedoria",
        output_path: str | None = None,
        descricao_custom: str = "",
        cenario_custom: str = "",
        nome_arquivo: str = "",
        phrase_context: str = "",
    ) -> str | None:
        """Gera uma imagem do mago para uma situacao.

        Args:
            phrase_context: frase para contextualizar o background (opcional).
                Quando fornecido, o Gemini adapta a cena ao conteudo da frase.

        Returns:
            caminho da imagem gerada ou None se falhar
        """
        self._load_referencias()

        if not self._referencias:
            logger.error("Nenhuma imagem de referencia disponivel")
            return None

        refs = _selecionar_referencias(self._referencias, n=self.n_referencias)
        prompt_texto = construir_prompt_completo(
            situacao_key, descricao_custom, cenario_custom, phrase_context
        )

        partes = []
        for img in refs:
            partes.append(_pil_para_part(img))
        partes.append(
            "These are reference images of the character. "
            "Replicate the character visual style EXACTLY in your generation."
        )
        partes.append(prompt_texto)

        logger.info(f"Gerando: situacao={situacao_key}, refs={len(refs)}")

        imagem = self._tentar_modelos(partes, self.temperatura)

        if imagem is None:
            logger.error("Todos os modelos falharam")
            return None

        if output_path:
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            imagem.save(output_path, "PNG")
            return output_path

        nome = nome_arquivo or f"mago_{situacao_key}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return self._salvar(imagem, nome)

    def refine_image(
        self,
        imagem_base: PIL.Image.Image,
        instrucao: str = "",
        referencias_adicionais: int = 3,
        nome_arquivo: str = "",
    ) -> str | None:
        """Refina uma imagem existente (img2img com temperatura baixa).

        Returns:
            caminho da imagem refinada ou None se falhar
        """
        self._load_referencias()

        partes = []
        partes.append("THIS IS THE IMAGE TO REFINE. Keep the exact same composition and character:")
        partes.append(_pil_para_part(imagem_base))

        if self._referencias and referencias_adicionais > 0:
            refs = _selecionar_referencias(self._referencias, n=referencias_adicionais)
            partes.append(
                f"These {len(refs)} images are the ORIGINAL CHARACTER REFERENCES for consistency:"
            )
            for r in refs:
                partes.append(_pil_para_part(r))

        instrucao_final = instrucao or (
            "Refine this image maintaining the EXACT same composition, pose, and scene. "
            "Improve character consistency with the reference images. "
            "Ensure all character DNA traits are precisely correct."
        )

        prompt = (
            f"{instrucao_final}\n\n"
            f"CHARACTER TRAITS TO ALWAYS MAINTAIN:\n{CHARACTER_DNA}\n\n"
            f"COMPOSITION TO MAINTAIN:\n{COMPOSITION}\n\n"
            f"DO NOT CHANGE:\n"
            f"- The overall composition and pose\n"
            f"- The background scene and mood\n"
            f"- The character action and expression\n\n"
            f"IMPROVE:\n"
            f"- Character consistency with reference images\n"
            f"- Color accuracy (strict palette: hat #4A5568, robes #1A1A3E, staff glow #FFD54F)\n"
            f"- Beard length and flow (must reach chest, white/silver, wavy)\n"
            f"- Hat shape (tall, pointed, bent tip, NEVER removed)\n"
            f"- Detail sharpness and photorealistic textures\n"
            f"- Gold embroidery on robes visibility"
        )

        partes.append(prompt)

        logger.info(f"Refinando imagem (refs adicionais: {referencias_adicionais})")

        imagem = self._tentar_modelos(partes, temperatura=0.4)

        if imagem is None:
            logger.error("Refinamento falhou em todos os modelos")
            return None

        nome = nome_arquivo or f"mago_refinado_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        return self._salvar(imagem, nome)

    def generate_with_refinement(
        self,
        situacao_key: str = "sabedoria",
        descricao_custom: str = "",
        cenario_custom: str = "",
        passes_refinamento: int = 1,
        instrucao_refinamento: str = "",
        nome_arquivo: str = "",
    ) -> str | None:
        """Pipeline Nano Banana: geracao + N passes de refinamento.

        Returns:
            caminho da imagem final ou None se falhar
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_nome = nome_arquivo or f"mago_{situacao_key}_{ts}"

        logger.info(f"Pipeline Nano Banana: {situacao_key} ({passes_refinamento} passes)")

        # Geracao inicial
        path_v0 = self.generate_image(
            situacao_key=situacao_key,
            descricao_custom=descricao_custom,
            cenario_custom=cenario_custom,
            nome_arquivo=f"{base_nome}_v0",
        )

        if path_v0 is None:
            return None

        img = PIL.Image.open(path_v0).convert("RGB")
        last_path = path_v0

        # Passes de refinamento
        for i in range(passes_refinamento):
            logger.info(f"Refinamento {i + 1}/{passes_refinamento}")
            time.sleep(5)

            ref_path = self.refine_image(
                imagem_base=img,
                instrucao=instrucao_refinamento,
                referencias_adicionais=min(4, self.n_referencias),
                nome_arquivo=f"{base_nome}_v{i + 1}",
            )

            if ref_path is not None:
                img = PIL.Image.open(ref_path).convert("RGB")
                last_path = ref_path
            else:
                logger.warning(f"Refinamento {i + 1} falhou, mantendo versao anterior")
                break

        # Salvar versao final
        final_path = self._salvar(img, f"{base_nome}_final")
        logger.info(f"FINAL: {final_path}")
        return final_path

    # ===== Async wrappers =====

    async def agenerate_image(
        self,
        situacao_key: str = "sabedoria",
        output_path: str | None = None,
        descricao_custom: str = "",
        cenario_custom: str = "",
        semaphore: asyncio.Semaphore | None = None,
        phrase_context: str = "",
    ) -> str | None:
        """Versao async de generate_image."""
        async def _call():
            return await asyncio.to_thread(
                lambda: self.generate_image(
                    situacao_key=situacao_key,
                    output_path=output_path,
                    descricao_custom=descricao_custom,
                    cenario_custom=cenario_custom,
                    phrase_context=phrase_context,
                )
            )
        if semaphore:
            async with semaphore:
                return await _call()
        return await _call()

    async def agenerate_with_refinement(
        self,
        situacao_key: str = "sabedoria",
        descricao_custom: str = "",
        cenario_custom: str = "",
        passes_refinamento: int = 1,
        semaphore: asyncio.Semaphore | None = None,
    ) -> str | None:
        """Versao async de generate_with_refinement."""
        async def _call():
            return await asyncio.to_thread(
                self.generate_with_refinement,
                situacao_key, descricao_custom, cenario_custom, passes_refinamento,
            )
        if semaphore:
            async with semaphore:
                return await _call()
        return await _call()

    def generate_for_topic(
        self, topic, output_path: str | None = None,
        phrase_context: str = "",
    ) -> str | None:
        """Gera imagem a partir de um AnalyzedTopic ou string.

        Args:
            phrase_context: frase para contextualizar o background.
                Quando fornecido, o cenario reflete o conteudo da frase.
        """
        if isinstance(topic, str):
            situacao_key = _mapear_situacao(topic)
        else:
            situacao_key = _mapear_situacao(
                topic.gandalf_topic, getattr(topic, "humor_angle", "")
            )
        return self.generate_image(
            situacao_key=situacao_key, output_path=output_path,
            phrase_context=phrase_context,
        )

    async def agenerate_for_topic(
        self, topic, output_path: str | None = None,
        semaphore: asyncio.Semaphore | None = None,
        phrase_context: str = "",
    ) -> str | None:
        """Versao async de generate_for_topic.

        Args:
            phrase_context: frase para contextualizar o background.
                Quando fornecido, o cenario reflete o conteudo da frase.
        """
        if isinstance(topic, str):
            situacao_key = _mapear_situacao(topic)
        else:
            situacao_key = _mapear_situacao(
                topic.gandalf_topic, getattr(topic, "humor_angle", "")
            )
        return await self.agenerate_image(
            situacao_key=situacao_key, output_path=output_path,
            semaphore=semaphore, phrase_context=phrase_context,
        )
