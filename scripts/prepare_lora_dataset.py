"""Prepara dataset das imagens do Mago Mestre para treinamento de LoRA.

Processa as imagens de assets/backgrounds/mago/:
- Redimensiona para 768x768 (center crop)
- Gera captions .txt com descricao do personagem + acao

Uso:
    python scripts/prepare_lora_dataset.py
"""

import re
from pathlib import Path

from PIL import Image

# Diretorios
CLIP_FLOW_DIR = Path(__file__).parent.parent
SOURCE_DIR = CLIP_FLOW_DIR / "assets" / "backgrounds" / "mago"
DATASET_DIR = CLIP_FLOW_DIR / "lora_training" / "dataset" / "1_ohwx_mago"

# Resolucao de treino (768x768 otimizado para 8GB VRAM)
TRAIN_SIZE = 768

# DNA base do personagem para captions
BASE_CAPTION = (
    "ohwx_mago, semi-realistic cartoon elderly wizard, "
    "long white wavy beard reaching chest, tall pointed blue-grey hat with wide brim, "
    "dark midnight blue flowing robes with subtle gold embroidery trim, "
    "brown leather belt with gold buckle, gnarled dark wooden staff with golden glowing tip, "
    "bright blue twinkling eyes, warm wise expression, thick white eyebrows"
)

# Mapa de palavras-chave no filename para descricoes de acao
ACTION_MAP = {
    "front_pose": "standing front-facing pose, neutral expression, holding staff",
    "portrait": "close-up portrait, wise knowing expression, detailed face",
    "casting_magic": "casting magic spell, magical energy from staff, dramatic lighting",
    "spell_gesture": "hand raised casting spell, magical particles, mystical energy",
    "staff_raised": "staff raised high, dramatic pose, powerful stance",
    "meditando": "sitting cross-legged meditating, peaceful serene expression, floating staff",
    "atacando_sombras": "fighting shadow creatures, defensive stance, staff glowing bright",
    "com_copo": "holding a goblet, relaxed amused expression, tavern setting",
    "comprimido": "looking at a pill or small object, confused expression",
    "cozinhando_pocao": "stirring a bubbling cauldron, potion brewing, magical ingredients",
    "dormindo": "sleeping peacefully in armchair, staff leaning against wall, soft lighting",
    "escrevendo_pergaminho": "writing on a scroll with quill, focused expression, candlelight",
    "invocando_criatura": "summoning a magical creature, hands outstretched, ethereal glow",
    "jardinagem_magica": "tending a magical garden, glowing plants, peaceful outdoor setting",
    "lendo_grimorio": "reading a large tome, concentrated expression, floating books",
    "levitando_cachimbo": "levitating a pipe with magic, amused expression, smoke swirls",
    "olhando_cristal": "gazing into a crystal ball, mystical glow, prophetic expression",
    "tocando_harpa": "playing a magical harp, musical notes floating, serene expression",
    "tomando_cafe": "drinking from a mug, content relaxed expression, morning setting",
}


def extract_action(filename: str) -> str:
    """Extrai descricao de acao baseada no nome do arquivo."""
    name = filename.lower().replace(".png", "").replace(".jpg", "").replace(".webp", "")

    # Remover prefixos comuns e numeros
    name = re.sub(r"^(grey_wizard_|mago_mestre_|image\d*_mago_mestre_)", "", name)
    name = re.sub(r"_?\d+$", "", name)

    for keyword, action in ACTION_MAP.items():
        if keyword in name:
            return action

    return "standing pose, wise expression, holding staff"


def center_crop_resize(img: Image.Image, target_size: int) -> Image.Image:
    """Crop central e resize para target_size x target_size."""
    w, h = img.size
    # Crop para quadrado
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side))
    # Resize
    img = img.resize((target_size, target_size), Image.LANCZOS)
    return img


def main():
    print(f"Preparando dataset para treinamento de LoRA")
    print(f"  Fonte: {SOURCE_DIR}")
    print(f"  Destino: {DATASET_DIR}")
    print(f"  Resolucao: {TRAIN_SIZE}x{TRAIN_SIZE}")
    print()

    if not SOURCE_DIR.exists():
        print(f"ERRO: Diretorio nao encontrado: {SOURCE_DIR}")
        print("Coloque as imagens do mago em assets/backgrounds/mago/")
        return

    DATASET_DIR.mkdir(parents=True, exist_ok=True)

    extensions = ("*.png", "*.jpg", "*.jpeg", "*.webp")
    source_images = []
    for ext in extensions:
        source_images.extend(SOURCE_DIR.glob(ext))

    if not source_images:
        print(f"ERRO: Nenhuma imagem encontrada em {SOURCE_DIR}")
        return

    print(f"  {len(source_images)} imagens encontradas\n")

    for img_path in sorted(source_images):
        name = img_path.stem
        output_img = DATASET_DIR / f"{name}.png"
        output_txt = DATASET_DIR / f"{name}.txt"

        # Processar imagem
        img = Image.open(img_path).convert("RGB")
        img_resized = center_crop_resize(img, TRAIN_SIZE)
        img_resized.save(output_img, "PNG")

        # Gerar caption
        action = extract_action(img_path.name)
        caption = f"{BASE_CAPTION}, {action}"
        output_txt.write_text(caption, encoding="utf-8")

        print(f"  {img_path.name}")
        print(f"    -> {output_img.name} ({TRAIN_SIZE}x{TRAIN_SIZE})")
        print(f"    -> {output_txt.name}: ...{action}")

    print(f"\nDataset pronto: {len(source_images)} imagens em {DATASET_DIR}")
    print(f"\nProximo passo: python scripts/train_lora.py")


if __name__ == "__main__":
    main()
