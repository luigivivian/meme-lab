"""Construtor de prompts para geracao de imagens via ComfyUI.

Mapeia AnalyzedTopic -> prompt de imagem completo,
incluindo DNA do personagem, cenario tematico e composicao.
"""

import logging

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
    # Alias: relaxando = descanso (compatibilidade com SITUACOES do gemini_client)
    "relaxando": (
        "blissfully asleep expression, sitting in comfortable wooden chair, "
        "hat tipped over eyes, hands folded on belly, staff leaning against wall"
    ),
    "meditando": (
        "eyes closed, serene peaceful smile, sitting cross-legged, "
        "staff hovering beside, subtle ethereal blue-gold aura radiating outward"
    ),
    "confronto": (
        "stern determined expression, staff raised high with intense golden energy, "
        "one hand extended forward in STOP gesture, dramatic wind blowing robes"
    ),
    "surpresa": (
        "wide eyes of genuine shock, mouth open in surprise, both hands raised, "
        "hat blown slightly back, exclamation sparks floating around"
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
    "medita": "meditando",
    "zen": "meditando",
    "yoga": "meditando",
    "relaxa": "relaxando",
    "descanso": "relaxando",
    "confronto": "confronto",
    "briga": "confronto",
    "nao passa": "confronto",
    "surpresa": "surpresa",
    "choque": "surpresa",
    "espanto": "surpresa",
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
    # Aliases para compatibilidade com SITUACOES do gemini_client
    "relaxando": [
        "mago_mestre_dormindo_1.png",
        "mago_mestre_meditando_1.png",
    ],
    "meditando": [
        "mago_mestre_meditando_1.png",
        "image2_mago_mestre_meditando_1.png",
    ],
    "confronto": [
        "grey_wizard_staff_raised_1.png",
        "grey_wizard_casting_magic_1.png",
        "mago_mestre_invocando_criatura_1.png",
    ],
    "surpresa": [
        "grey_wizard_casting_magic_1.png",
        "mago_mestre_olhando_cristal_1.png",
    ],
    "generico": [
        "grey_wizard_front_pose_1.png",
        "grey_wizard_portrait_1.png",
        "grey_wizard_spell_gesture_1.png",
    ],
}


def select_reference_image(topic, reference_dir: str | None = None, situacao_key: str = "") -> str | None:
    """Seleciona a melhor imagem de referencia para um topico.

    Args:
        topic: AnalyzedTopic ou string com o tema.
        reference_dir: Diretorio com as imagens de referencia.
        situacao_key: Chave de situacao definida pelo Curator (prioridade sobre keyword matching).

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

    # Determinar cenario — prioridade: situacao_key > keyword matching
    if situacao_key and situacao_key in REFERENCE_MAP:
        scene_key = situacao_key
    elif situacao_key and situacao_key in SCENE_TEMPLATES:
        scene_key = situacao_key
    else:
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


def _match_scene(topic: str, humor_angle: str, situacao_key: str = "") -> str:
    """Mapeia um topico + angulo de humor para um template de cenario.

    Se situacao_key fornecida e valida, usa direto (sem keyword matching).
    """
    if situacao_key and situacao_key in SCENE_TEMPLATES:
        logger.debug(f"Cenario via situacao_key: {situacao_key}")
        return SCENE_TEMPLATES[situacao_key]

    combined = f"{topic} {humor_angle}".lower()
    for keyword, scene_key in KEYWORD_MAP.items():
        if keyword in combined:
            logger.debug(f"Cenario via keyword '{keyword}': {scene_key}")
            return SCENE_TEMPLATES[scene_key]
    logger.debug("Cenario fallback: generico")
    return SCENE_TEMPLATES["generico"]


def build_prompt(topic, situacao_key: str = "") -> str:
    """Constroi prompt completo para geracao de imagem a partir de um topico analisado.

    Versao estatica — zero API calls, rapido e gratis.
    Aceita AnalyzedTopic ou string.
    """
    if isinstance(topic, str):
        scene = _match_scene(topic, "", situacao_key=situacao_key)
    else:
        scene = _match_scene(topic.gandalf_topic, topic.humor_angle, situacao_key=situacao_key)

    prompt = f"{CHARACTER_DNA}, {scene}, {COMPOSITION}"
    logger.debug(f"Prompt estatico gerado (situacao={situacao_key}): {prompt[:100]}...")
    return prompt


def build_prompt_with_llm(topic, situacao_key: str = "") -> str:
    """Gera prompt hibrido: SCENE_TEMPLATE obrigatorio + detalhes criativos via LLM.

    A cena base (CHARACTER_DNA + SCENE_TEMPLATE + COMPOSITION) e sempre inclusa.
    O LLM apenas adiciona detalhes ambientais criativos (iluminacao, particulas, mood).
    Isso garante que o tema visual e SEMPRE respeitado, independente do modelo LLM.

    Fallback para build_prompt() se a API falhar.
    Aceita AnalyzedTopic ou string.
    """
    if isinstance(topic, str):
        gandalf_topic = topic
        humor_angle = "humor leve e relatable"
    else:
        gandalf_topic = topic.gandalf_topic
        humor_angle = topic.humor_angle

    # Base obrigatoria: cena deterministica do SCENE_TEMPLATES
    scene = _match_scene(gandalf_topic, humor_angle, situacao_key=situacao_key)

    try:
        from src.llm_client import generate

        # LLM gera APENAS detalhes extras (iluminacao, particulas, mood)
        extras = generate(
            system_prompt=(
                "You generate SHORT creative detail additions for Stable Diffusion prompts. "
                "You receive a base scene description of an elderly wizard character. "
                "Add ONLY 2-3 short atmospheric/lighting/particle details in English. "
                "Examples: 'warm golden rim light, dust motes floating, soft bokeh background' "
                "or 'dramatic volumetric fog, blue magical particles, cinematic lighting'. "
                "Reply with ONLY the extra details, no explanation, no character description, "
                "no pose, no expression — those are already in the base prompt."
            ),
            user_message=(
                f"Base scene: '{scene}'\n"
                f"Topic context: '{gandalf_topic}' with humor angle: '{humor_angle}'\n"
                f"Visual theme: '{situacao_key}'\n"
                f"Add 2-3 atmospheric detail phrases (lighting, particles, mood):"
            ),
            max_tokens=100,
            tier="lite",
        ).strip()

        # Limpar resposta do LLM (remover aspas, prefixos comuns)
        extras = extras.strip('"\'').strip()
        if extras.lower().startswith("here"):
            extras = ""
        if extras.lower().startswith("base scene"):
            extras = ""

        # Montar prompt hibrido: DNA + cena obrigatoria + extras LLM + composicao
        # CHARACTER_DNA ja começa com "ohwx_mago, ..."
        parts = [CHARACTER_DNA, scene]
        if extras and len(extras) < 200:
            parts.append(extras)
        parts.append(COMPOSITION)

        prompt = ", ".join(parts)
        logger.info(
            f"Prompt hibrido (situacao={situacao_key}): "
            f"scene='{scene[:60]}...' extras='{extras[:60]}...'"
        )
        return prompt

    except Exception as e:
        logger.warning(f"Falha no LLM para extras de prompt: {e}")
        return build_prompt(topic, situacao_key=situacao_key)
