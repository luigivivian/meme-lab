"""Construtor de prompts para geracao de imagens via ComfyUI.

Mapeia AnalyzedTopic -> prompt de imagem completo,
incluindo DNA do personagem, cenario tematico e composicao.
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("clip-flow.prompt_builder")

# DNA imutavel do personagem — aparece em TODO prompt
# Baseado nas 20 imagens de referencia em assets/backgrounds/mago/
CHARACTER_DNA = (
    "ohwx_mago, single elderly wizard character, "
    "watercolor gouache digital painting, fantasy concept art illustration, "
    "tall pointed dark charcoal grey hat with wide brim and forward-bent tip, "
    "very long straight white silver beard reaching chest, "
    "dark charcoal grey layered flowing robes with subtle celtic runic embroidery on trim, "
    "dark grey sash belt at waist, multiple fabric layers visible, "
    "gnarled twisted dark brown wooden staff, "
    "deeply weathered wrinkled face, prominent nose, "
    "intense piercing bright blue eyes, thick grey eyebrows, "
    "realistic human proportions, muted monochromatic color palette"
)

# Composicao padrao para Instagram 4:5
COMPOSITION = (
    "Vertical 4:5 aspect ratio, character centered in lower two thirds of frame, "
    "upper area open for text overlay, "
    "clean white off-white background, character isolated on plain background, "
    "soft diffused lighting, high detail painterly brushstrokes, "
    "fantasy book illustration quality"
)

# Cenarios tematicos pre-definidos
# Fundo sempre branco/limpo como nas referencias, acao via props e expressao
SCENE_TEMPLATES = {
    "cotidiano": (
        "relaxed warm expression, holding a wooden ale mug, "
        "slight smile, soft magical sparkles around mug"
    ),
    "trabalho": (
        "sitting at wooden desk, anachronistic glowing laptop, "
        "focused concentrated expression, blue magical glow from screen"
    ),
    "segunda_feira": (
        "tired sleepy expression, holding steaming coffee goblet with both hands, "
        "hat slightly drooping, eyes half closed, steam with magical sparkles"
    ),
    "tecnologia": (
        "holding glowing smartphone, confused amused expression, "
        "hat slightly askew, floating digital runes around device"
    ),
    "comida": (
        "stirring bubbling cauldron with ladle, floating magical ingredients, "
        "colorful potion vapors rising, focused expression"
    ),
    "relacionamento": (
        "gentle knowing smile, holding glowing heart-shaped crystal, "
        "soft pink and blue magical aura around hands"
    ),
    "sabedoria": (
        "wise contemplative expression, leaning on staff, "
        "eyes glowing faintly blue, subtle golden magical aura"
    ),
    "confusao": (
        "bewildered expression, head tilted, scratching beard with one hand, "
        "floating question mark shaped magical sparks"
    ),
    "vitoria": (
        "triumphant expression, staff raised high above head, "
        "golden magical particles and sparkles erupting from staff tip"
    ),
    "descanso": (
        "peaceful sleeping expression, sitting in wooden chair, "
        "hat covering eyes, staff leaning nearby, floating blue particles"
    ),
    "internet": (
        "looking at glowing crystal ball like a screen, surprised amused expression, "
        "hat slightly askew, blue glow reflecting on face"
    ),
    "cafe": (
        "holding ornate steaming coffee mug, content pleased expression, "
        "steam rising with golden magical sparkles, slight warm smile"
    ),
    "generico": (
        "standing pose holding staff, wise serious expression, "
        "subtle blue magical glow from staff crystal tip"
    ),
}

# Mapa de palavras-chave para cenarios
KEYWORD_MAP = {
    "segunda": "segunda_feira",
    "monday": "segunda_feira",
    "cafe": "cafe",
    "coffee": "cafe",
    "trabalho": "trabalho",
    "work": "trabalho",
    "emprego": "trabalho",
    "chefe": "trabalho",
    "escritorio": "trabalho",
    "wifi": "tecnologia",
    "internet": "internet",
    "celular": "internet",
    "rede social": "internet",
    "instagram": "internet",
    "tiktok": "internet",
    "comida": "comida",
    "cozinha": "comida",
    "almoco": "comida",
    "jantar": "comida",
    "namoro": "relacionamento",
    "crush": "relacionamento",
    "ex": "relacionamento",
    "relacionamento": "relacionamento",
    "sabedoria": "sabedoria",
    "conselho": "sabedoria",
    "verdade": "sabedoria",
    "preguica": "descanso",
    "sono": "descanso",
    "dormir": "descanso",
    "feriado": "descanso",
    "ferias": "descanso",
    "vitoria": "vitoria",
    "sucesso": "vitoria",
    "confuso": "confusao",
    "entender": "confusao",
}


# Mapa de cenarios para imagens de referencia (filenames em assets/backgrounds/mago/)
# Cada cenario pode ter multiplas referencias — uma e escolhida aleatoriamente
REFERENCE_MAP = {
    "cotidiano": [
        "mago_mestre_com_copo_1.png",
        "mago_mestre_levitando_cachimbo_1.png",
    ],
    "trabalho": [
        "mago_mestre_escrevendo_pergaminho_1.png",
        "mago_mestre_lendo_grimorio_1.png",
    ],
    "segunda_feira": [
        "mago_mestre_tomando_cafe_1.png",
        "mago_mestre_dormindo_1.png",
    ],
    "tecnologia": [
        "mago_mestre_olhando_cristal_1.png",
        "mago_mestre_lendo_grimorio_1.png",
    ],
    "comida": [
        "mago_mestre_cozinhando_pocao_1.png",
        "mago_mestre_com_copo_1.png",
    ],
    "relacionamento": [
        "mago_mestre_olhando_cristal_1.png",
        "mago_mestre_tocando_harpa_1.png",
    ],
    "sabedoria": [
        "mago_mestre_meditando_1.png",
        "mago_mestre_lendo_grimorio_1.png",
        "grey_wizard_portrait_1.png",
    ],
    "confusao": [
        "grey_wizard_casting_magic_1.png",
        "mago_mestre_olhando_cristal_1.png",
    ],
    "vitoria": [
        "grey_wizard_staff_raised_1.png",
        "grey_wizard_casting_magic_1.png",
        "mago_mestre_invocando_criatura_1.png",
    ],
    "descanso": [
        "mago_mestre_dormindo_1.png",
        "mago_mestre_meditando_1.png",
        "image2_mago_mestre_meditando_1.png",
    ],
    "internet": [
        "mago_mestre_olhando_cristal_1.png",
        "mago_mestre_lendo_grimorio_1.png",
    ],
    "cafe": [
        "mago_mestre_tomando_cafe_1.png",
        "mago_mestre_com_copo_1.png",
    ],
    "generico": [
        "grey_wizard_front_pose_1.png",
        "grey_wizard_portrait_1.png",
        "grey_wizard_spell_gesture_1.png",
    ],
}


def select_reference_image(topic, reference_dir: str | None = None) -> str | None:
    """Seleciona a melhor imagem de referencia para um topico.

    Args:
        topic: AnalyzedTopic ou string com o tema.
        reference_dir: Diretorio com as imagens de referencia.

    Returns:
        Caminho absoluto da imagem de referencia, ou None.
    """
    import random
    from pathlib import Path

    if reference_dir is None:
        from config import COMFYUI_REFERENCE_DIR
        reference_dir = str(COMFYUI_REFERENCE_DIR)

    ref_path = Path(reference_dir)
    if not ref_path.exists():
        logger.warning(f"Diretorio de referencias nao encontrado: {reference_dir}")
        return None

    # Determinar cenario
    if isinstance(topic, str):
        combined = topic.lower()
    else:
        combined = f"{topic.gandalf_topic} {topic.humor_angle}".lower()

    scene_key = "generico"
    for keyword, key in KEYWORD_MAP.items():
        if keyword in combined:
            scene_key = key
            break

    # Buscar imagens de referencia para o cenario
    candidates = REFERENCE_MAP.get(scene_key, REFERENCE_MAP["generico"])
    existing = [str(ref_path / name) for name in candidates if (ref_path / name).exists()]

    if not existing:
        # Fallback: qualquer imagem do diretorio
        all_images = list(ref_path.glob("*.png")) + list(ref_path.glob("*.jpg"))
        if all_images:
            chosen = str(random.choice(all_images))
            logger.debug(f"Referencia fallback: {chosen}")
            return chosen
        return None

    chosen = random.choice(existing)
    logger.info(f"Referencia selecionada ({scene_key}): {Path(chosen).name}")
    return chosen


def _match_scene(topic: str, humor_angle: str) -> str:
    """Mapeia um topico + angulo de humor para um template de cenario."""
    combined = f"{topic} {humor_angle}".lower()
    for keyword, scene_key in KEYWORD_MAP.items():
        if keyword in combined:
            return SCENE_TEMPLATES[scene_key]
    return SCENE_TEMPLATES["generico"]


def build_prompt(topic) -> str:
    """Constroi prompt completo para geracao de imagem a partir de um topico analisado.

    Versao estatica — zero API calls, rapido e gratis.
    Aceita AnalyzedTopic ou string.
    """
    if isinstance(topic, str):
        scene = _match_scene(topic, "")
    else:
        scene = _match_scene(topic.gandalf_topic, topic.humor_angle)

    prompt = f"{CHARACTER_DNA}, {scene}, {COMPOSITION}"
    logger.debug(f"Prompt estatico gerado: {prompt[:100]}...")
    return prompt


def build_prompt_with_claude(topic) -> str:
    """Usa Claude para gerar um prompt de imagem mais criativo e especifico.

    Fallback para build_prompt() se a API falhar.
    Aceita AnalyzedTopic ou string.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key == "your-api-key-here":
        logger.warning("ANTHROPIC_API_KEY nao configurada, usando prompt estatico")
        return build_prompt(topic)

    if isinstance(topic, str):
        gandalf_topic = topic
        humor_angle = "humor leve e relatable"
    else:
        gandalf_topic = topic.gandalf_topic
        humor_angle = topic.humor_angle

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            system=(
                "Voce gera prompts curtos para Stable Diffusion / Flux. "
                "O personagem e SEMPRE o mesmo: um mago idoso cartoon semi-realista "
                "com barba branca longa, chapeu pontudo cinza-azulado, tunica azul noturno "
                "com detalhes dourados, cajado de madeira com brilho dourado, olhos azuis. "
                "Responda APENAS com o prompt em ingles, uma unica linha, sem explicacao."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Crie um prompt de imagem para o cenario: '{gandalf_topic}' "
                    f"com angulo de humor: '{humor_angle}'. "
                    f"O mago deve estar no terco inferior, area superior livre para texto. "
                    f"Formato vertical 4:5, atmosfera escura mistica com iluminacao dourada. "
                    f"Comece com 'ohwx_mago' como trigger word."
                ),
            }],
        )
        prompt = message.content[0].text.strip()

        # Garantir trigger word
        if not prompt.lower().startswith("ohwx_mago"):
            prompt = f"ohwx_mago, {prompt}"

        # Garantir composicao
        if "vertical" not in prompt.lower():
            prompt += f", {COMPOSITION}"

        logger.info(f"Prompt via Claude: {prompt[:100]}...")
        return prompt

    except Exception as e:
        logger.warning(f"Falha no Claude para prompt de imagem: {e}")
        return build_prompt(topic)
