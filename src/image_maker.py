import io
import os
import sys
import unicodedata

from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import (
    IMAGE_WIDTH,
    IMAGE_HEIGHT,
    TEXT_COLOR,
    TEXT_STROKE_COLOR,
    TEXT_STROKE_WIDTH,
    SHADOW_COLOR,
    SHADOW_OFFSET,
    OVERLAY_COLOR,
    VIGNETTE_STRENGTH,
    GLOW_COLOR,
    FONT_SIZE,
    WATERMARK_FONT_SIZE,
    WATERMARK_COLOR,
    WATERMARK_TEXT,
    TEXT_VERTICAL_POSITION,
    FONTS_DIR,
    OUTPUT_DIR,
    GENERATED_MEMES_DIR,
    LAYOUT_TEMPLATES,
    LAYOUT_DEFAULT,
)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """Carrega fonte customizada ou fallback do sistema."""
    for font_file in FONTS_DIR.glob("*.ttf"):
        return ImageFont.truetype(str(font_file), size)
    for font_file in FONTS_DIR.glob("*.otf"):
        return ImageFont.truetype(str(font_file), size)

    system_fonts = [
        "C:/Windows/Fonts/impact.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for font_path in system_fonts:
        if os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)

    return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Quebra texto em linhas que cabem na largura maxima."""
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        bbox = font.getbbox(test_line)
        text_width = bbox[2] - bbox[0]

        if text_width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines if lines else [text]


def _crop_center(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """Redimensiona e corta a imagem para o tamanho alvo mantendo proporcao."""
    img_ratio = img.width / img.height
    target_ratio = target_w / target_h

    if img_ratio > target_ratio:
        new_height = target_h
        new_width = int(target_h * img_ratio)
    else:
        new_width = target_w
        new_height = int(target_w / img_ratio)

    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    left = (new_width - target_w) // 2
    top = (new_height - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))


def _create_vignette(width: int, height: int, strength: int) -> Image.Image:
    """Cria mascara de vinheta escura nas bordas — efeito mistico."""
    vignette = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(vignette)

    # Elipse branca no centro, bordas escuras
    margin_x = int(width * 0.15)
    margin_y = int(height * 0.10)
    draw.ellipse(
        [margin_x, margin_y, width - margin_x, height - margin_y],
        fill=255,
    )

    # Blur forte para suavizar a transicao
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=width // 4))

    # Converter para mascara RGBA (preto com alpha variavel)
    vignette_rgba = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    for y in range(height):
        for x in range(width):
            lum = vignette.getpixel((x, y))
            # Inverter: branco no centro = transparente, preto nas bordas = escuro
            alpha = int((255 - lum) / 255 * strength)
            vignette_rgba.putpixel((x, y), (0, 0, 0, alpha))

    return vignette_rgba


def _create_vignette_fast(width: int, height: int, strength: int) -> Image.Image:
    """Cria vinheta de forma otimizada usando operacoes de imagem."""
    # Mascara de luminosidade: branco no centro, preto nas bordas
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)

    margin_x = int(width * 0.15)
    margin_y = int(height * 0.10)
    draw.ellipse(
        [margin_x, margin_y, width - margin_x, height - margin_y],
        fill=255,
    )
    mask = mask.filter(ImageFilter.GaussianBlur(radius=width // 4))

    # Camada preta completa
    dark = Image.new("RGBA", (width, height), (0, 0, 0, strength))

    # Usar mascara invertida como alpha — bordas escuras, centro transparente
    from PIL import ImageChops
    inverted_mask = ImageChops.invert(mask)

    # Escalar alpha pelo strength
    alpha_channel = inverted_mask.point(lambda p: int(p * strength / 255))
    dark.putalpha(alpha_channel)

    return dark


def _create_glow_layer(
    width: int,
    height: int,
    glow_color: tuple,
    text_vertical_position: float = TEXT_VERTICAL_POSITION,
) -> Image.Image:
    """Cria camada de brilho dourado sutil centralizada na posicao do texto.

    Args:
        width: largura da imagem.
        height: altura da imagem.
        glow_color: cor RGBA do glow (ex: 255,200,80,15).
        text_vertical_position: posicao vertical do texto (0.0=topo, 1.0=base).
    """
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)

    cx, cy = width // 2, int(height * text_vertical_position)
    radius = int(width * 0.5)
    r, g, b, a = glow_color

    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=(r, g, b, a),
    )

    glow = glow.filter(ImageFilter.GaussianBlur(radius=radius // 2))
    return glow


def create_image(
    text: str,
    background_path: str,
    output_path: str | None = None,
    watermark_text: str | None = None,
    layout: str | None = None,
) -> str:
    """Cria imagem com texto sobreposto usando layout configuravel.

    Composicao: background -> overlay -> vinheta -> glow -> texto com contorno -> watermark

    Args:
        text: Frase para sobrepor na imagem.
        background_path: Caminho da imagem de fundo.
        output_path: Caminho de saida (opcional, gera automaticamente).
        watermark_text: Texto do watermark (None = usa WATERMARK_TEXT do config).
        layout: Template de layout ("bottom", "top", "center", "split_top").
            None = usa LAYOUT_DEFAULT do config.

    Returns:
        Caminho do arquivo gerado.
    """
    wm = watermark_text if watermark_text is not None else WATERMARK_TEXT

    # Resolver layout template
    layout_name = layout or LAYOUT_DEFAULT
    layout_config = LAYOUT_TEMPLATES.get(layout_name, LAYOUT_TEMPLATES[LAYOUT_DEFAULT])
    text_vpos = layout_config.get("text_vertical_position", TEXT_VERTICAL_POSITION)
    text_align = layout_config.get("text_align", "center")
    margin_left = layout_config.get("margin_left", 80)

    # Detect solid color hex string (per D-01, D-03)
    if isinstance(background_path, str) and background_path.startswith("#"):
        hex_color = background_path.lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join(c * 2 for c in hex_color)
        if len(hex_color) != 6:
            raise ValueError(f"Invalid hex color: {background_path}")
        try:
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        except ValueError:
            raise ValueError(f"Invalid hex color: {background_path}")
        bg = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), (r, g, b, 255))
    else:
        bg = Image.open(background_path).convert("RGBA")
        bg = _crop_center(bg, IMAGE_WIDTH, IMAGE_HEIGHT)

    # 1. Overlay azul noturno semi-transparente
    overlay = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), OVERLAY_COLOR)
    bg = Image.alpha_composite(bg, overlay)

    # 2. Vinheta escura nas bordas
    vignette = _create_vignette_fast(IMAGE_WIDTH, IMAGE_HEIGHT, VIGNETTE_STRENGTH)
    bg = Image.alpha_composite(bg, vignette)

    # 3. Glow dourado posicionado na area do texto
    glow = _create_glow_layer(IMAGE_WIDTH, IMAGE_HEIGHT, GLOW_COLOR, text_vpos)
    bg = Image.alpha_composite(bg, glow)

    draw = ImageDraw.Draw(bg)
    font = _load_font(FONT_SIZE)
    watermark_font = _load_font(WATERMARK_FONT_SIZE)

    # Margem depende do alinhamento
    margin = margin_left if text_align == "left" else 80
    max_text_width = IMAGE_WIDTH - (margin * 2)
    lines = _wrap_text(text.upper(), font, max_text_width)

    # Calcular altura total do bloco de texto
    line_spacing = 14
    line_heights = []
    for line in lines:
        bbox = font.getbbox(line)
        line_heights.append(bbox[3] - bbox[1])
    total_height = sum(line_heights) + line_spacing * (len(lines) - 1)

    # Posicao vertical baseada no layout
    y = int(IMAGE_HEIGHT * text_vpos) - (total_height // 2)
    y = max(margin, y)
    y = min(y, IMAGE_HEIGHT - total_height - 70)

    # Desenhar cada linha com contorno + sombra
    for i, line in enumerate(lines):
        bbox = font.getbbox(line)
        text_width = bbox[2] - bbox[0]

        # Alinhamento horizontal
        if text_align == "left":
            x = margin
        elif text_align == "right":
            x = IMAGE_WIDTH - text_width - margin
        else:
            x = (IMAGE_WIDTH - text_width) // 2

        # Sombra suave
        for s in range(3):
            offset = SHADOW_OFFSET + s
            shadow_alpha = SHADOW_COLOR[3] if len(SHADOW_COLOR) > 3 else 200
            shadow_fill = (SHADOW_COLOR[0], SHADOW_COLOR[1], SHADOW_COLOR[2], shadow_alpha // (s + 1))
            draw.text((x + offset, y + offset), line, font=font, fill=shadow_fill)

        # Contorno preto (stroke) para legibilidade
        draw.text(
            (x, y), line, font=font,
            fill=TEXT_COLOR,
            stroke_width=TEXT_STROKE_WIDTH,
            stroke_fill=TEXT_STROKE_COLOR,
        )

        y += line_heights[i] + line_spacing

    # Watermark — so aplica se wm nao for vazio (exportacao aplica separadamente)
    if wm:
        wm_bbox = watermark_font.getbbox(wm)
        wm_width = wm_bbox[2] - wm_bbox[0]
        if layout_name == "split_top":
            wm_x = 20  # Canto inferior esquerdo
        else:
            wm_x = IMAGE_WIDTH - wm_width - 20  # Canto inferior direito
        wm_y = IMAGE_HEIGHT - 50
        draw.text(
            (wm_x, wm_y), wm, font=watermark_font,
            fill=WATERMARK_COLOR,
        )

    # Converter para RGB e salvar
    final = bg.convert("RGB")

    if output_path is None:
        GENERATED_MEMES_DIR.mkdir(parents=True, exist_ok=True)
        slug = "_".join(text.lower().split()[:4])
        slug = unicodedata.normalize("NFKD", slug).encode("ascii", "ignore").decode()
        slug = "".join(c for c in slug if c.isalnum() or c == "_")[:40]
        output_path = str(GENERATED_MEMES_DIR / f"{slug}.png")

    final.save(output_path, quality=95)
    return output_path


def stamp_watermark(image_path: str, watermark_text: str | None = None) -> bytes:
    """Aplica watermark numa imagem e retorna os bytes PNG.

    Usado pelo export para aplicar watermark dinamicamente sem alterar o original.
    """
    wm = watermark_text if watermark_text is not None else WATERMARK_TEXT
    if not wm:
        with open(image_path, "rb") as f:
            return f.read()

    img = Image.open(image_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    font = _load_font(WATERMARK_FONT_SIZE)

    wm_bbox = font.getbbox(wm)
    wm_width = wm_bbox[2] - wm_bbox[0]
    wm_x = img.width - wm_width - 20
    wm_y = img.height - 50
    draw.text((wm_x, wm_y), wm, font=font, fill=WATERMARK_COLOR)

    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", quality=95)
    return buf.getvalue()


def create_placeholder_background(output_path: str) -> str:
    """Cria background placeholder com gradiente mistico para testes."""
    img = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT))
    draw = ImageDraw.Draw(img)

    # Gradiente azul noturno -> preto (estilo mistico)
    for y in range(IMAGE_HEIGHT):
        progress = y / IMAGE_HEIGHT
        r = int(15 * (1 - progress))
        g = int(15 * (1 - progress))
        b = int(50 * (1 - progress) + 10)
        draw.line([(0, y), (IMAGE_WIDTH, y)], fill=(r, g, b))

    font = _load_font(32)
    hint = "Adicione imagens do Mago em assets/backgrounds/"
    bbox = font.getbbox(hint)
    text_width = bbox[2] - bbox[0]
    x = (IMAGE_WIDTH - text_width) // 2
    draw.text((x, IMAGE_HEIGHT - 100), hint, font=font, fill=(80, 70, 50))

    img.save(output_path)
    return output_path
