# hotfix_dna.py — Upload para o Colab e execute: %run hotfix_dna.py
import textwrap

CHARACTER_DNA = (
    "Photorealistic fantasy portrait of an ancient wise wizard with the following EXACT traits (NEVER change):\n"
    "\n"
    "FACE & SKIN:\n"
    "- Approximately 90 years old, deeply wrinkled weathered skin with natural skin pores\n"
    "- Prominent aquiline nose, thick bushy silver-grey eyebrows\n"
    "- Piercing intense pale blue-grey eyes with depth, wisdom, and subtle moisture reflection\n"
    "- Weathered smile lines, age spots on temples, hyper realistic skin texture\n"
    "\n"
    "BEARD & HAIR:\n"
    "- Very long flowing silver-white beard reaching chest, slightly unkempt natural texture\n"
    "- Individual hair strands visible, natural grey-white gradients (NEVER short or neat)\n"
    "- Wispy silver hair visible under hat brim\n"
    "\n"
    "HAT:\n"
    "- Wide-brimmed tall pointed grey felt hat, aged and slightly bent at tip\n"
    "- Weathered fabric texture, subtle dust and wear marks (NEVER remove, NEVER clean/new looking)\n"
    "\n"
    "ROBES & CLOTHING:\n"
    "- Weathered charcoal-grey wool robes with natural fabric folds and weight\n"
    "- Dark midnight blue outer layer (#1A1A3E) with worn leather belt and aged brass buckle\n"
    "- Subtle silver-gold thread embroidery on edges, slightly frayed\n"
    "- Worn brown leather boots with creases and dust\n"
    "\n"
    "STAFF:\n"
    "- Massive gnarled wooden staff of dark twisted oak (#3E2723)\n"
    "- Ancient runes barely visible carved into wood grain\n"
    "- Faint warm ember-golden glow at the top (#FFD54F), like dying embers\n"
    "\n"
    "PHYSIQUE:\n"
    "- Tall, lean, slightly hunched posture conveying age and wisdom\n"
    "- Large weathered hands with visible veins and knuckles\n"
    "\n"
    "RENDERING STYLE:\n"
    "- Photorealistic cinematic portrait, 85mm lens f/1.8 equivalent\n"
    "- Natural subsurface skin scattering, cinematic color grading\n"
    "- Subtle film grain, studio-quality lighting\n"
    "- Hyper realistic fabric textures, 8K detail level\n"
    "- NO cartoon, NO cel-shading, NO flat colors, NO stylization\n"
    "\n"
    "COLOR PALETTE (strict reference):\n"
    "Beard/Hair: #E8E8F0 (silver-white) | Hat: #4A5568 (weathered grey) |\n"
    "Robes: #1A1A3E (dark midnight blue) | Gold details: #C8A84E (aged brass) |\n"
    "Staff: #3E2723 (dark oak) | Staff glow: #FFD54F (warm ember) | Eyes: #8FA8C8 (pale blue-grey)"
)

COMPOSITION = (
    "Vertical 4:5 aspect ratio (1080x1350 pixels).\n"
    "Character positioned in lower two-thirds of frame — lower third preferred.\n"
    "Upper 35-40% of image open and clear for text overlay.\n"
    "Shallow depth of field on background, f/1.8 bokeh effect.\n"
    "Soft dramatic side lighting, cinematic color grading.\n"
    "Dark atmospheric fantasy setting with warm golden accent rim lighting.\n"
    "Camera angle: slight low angle, eye-level to mid-chest framing."
)

NEGATIVE_TRAITS = (
    "NOT cartoon, NOT cel-shading, NOT flat colors, NOT anime/manga, NOT chibi, "
    "NOT stylized, NOT illustration, NOT watercolor, NOT oil painting brush strokes visible, "
    "NOT young wizard, NOT clean/new clothing, NOT bright saturated colors, "
    "NOT centered in frame, NOT bright white background, NOT without hat, NOT short beard, "
    "NOT threatening expression, NOT different colored robes, "
    "photorealism only, no stylization whatsoever"
)

# Tambem corrige construir_prompt_completo() para reforcar photorealism
def construir_prompt_completo(
    situacao_key="sabedoria",
    descricao_custom="",
    cenario_custom="",
):
    if situacao_key == "custom":
        acao = descricao_custom or "standing pose holding staff, wise expression"
        cenario = cenario_custom or "dark moody medieval forest with golden atmospheric lighting"
    else:
        sit = SITUACOES.get(situacao_key, SITUACOES["sabedoria"])
        acao = sit["acao"]
        cenario = sit["cenario"]

    return (
        "Generate a PHOTOREALISTIC cinematic portrait of this wizard character matching the reference images EXACTLY.\n\n"
        "CHARACTER (replicate precisely from reference):\n" + CHARACTER_DNA + "\n\n"
        "ACTION/POSE:\n" + acao + "\n\n"
        "SETTING/BACKGROUND:\n" + cenario + "\n\n"
        "COMPOSITION:\n" + COMPOSITION + "\n\n"
        "IMPORTANT — DO NOT:\n" + NEGATIVE_TRAITS + "\n\n"
        "RENDERING MANDATE: This must look like a photograph or VFX still, NOT a painting or illustration.\n"
        "Natural skin pores, wrinkles, realistic fabric folds, cinematic shadows, shallow DOF bokeh.\n\n"
        "The character must look IDENTICAL to the reference images in features, colors, and proportions.\n"
        "Only the pose, expression, action, and background should change."
    )


print("CHARACTER_DNA, COMPOSITION, NEGATIVE_TRAITS atualizados (photorealistic)")
print("construir_prompt_completo() atualizado com RENDERING MANDATE")
print(f"   DNA: {len(CHARACTER_DNA)} chars")
print(f"   Composition: {len(COMPOSITION)} chars")
print(f"   Negatives: {len(NEGATIVE_TRAITS)} chars")
