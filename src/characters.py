"""Characters — carrega e gerencia personagens multi-character.

Cada personagem e definido em characters/{slug}/character.yaml.
"""

import logging
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from config import BASE_DIR

logger = logging.getLogger("clip-flow.characters")

CHARACTERS_DIR = BASE_DIR / "characters"
DEFAULT_CHARACTER = "mago-mestre"


def _slugify(text: str) -> str:
    """Converte texto para slug seguro (ex: 'O Dragao Zoeiro' -> 'dragao-zoeiro')."""
    text = text.lower().strip()
    text = re.sub(r"[àáâãä]", "a", text)
    text = re.sub(r"[èéêë]", "e", text)
    text = re.sub(r"[ìíîï]", "i", text)
    text = re.sub(r"[òóôõö]", "o", text)
    text = re.sub(r"[ùúûü]", "u", text)
    text = re.sub(r"[ç]", "c", text)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text


@dataclass
class CharacterStyle:
    """Estilo visual de composicao da imagem final."""
    overlay_color: tuple = (10, 10, 30, 40)
    glow_color: tuple = (255, 200, 80, 15)
    text_color: tuple = (255, 255, 255)
    text_stroke_width: int = 2
    text_vertical_position: float = 0.80
    font_size: int = 48
    watermark_color: tuple = (200, 180, 130, 120)
    watermark_font_size: int = 22


@dataclass
class CharacterConfig:
    """Configuracao completa de um personagem."""

    # Identidade
    slug: str
    name: str
    handle: str = ""
    watermark: str = ""
    status: str = "draft"  # draft | refining | ready

    # Persona (LLM)
    system_prompt: str = ""
    humor_style: str = ""
    tone: str = ""
    catchphrases: list[str] = field(default_factory=list)
    rules_max_chars: int = 120
    rules_forbidden: list[str] = field(default_factory=list)

    # Visual DNA (Gemini Image)
    character_dna: str = ""
    negative_traits: str = ""
    composition: str = ""

    # Visual DNA (ComfyUI)
    comfyui_trigger_word: str = ""
    comfyui_character_dna: str = ""
    comfyui_lora_path: str = ""

    # Branding
    branded_hashtags: list[str] = field(default_factory=list)
    caption_prompt: str = ""

    # Estilo
    style: CharacterStyle = field(default_factory=CharacterStyle)

    # Refs config
    refs_min_approved: int = 5
    refs_ideal_approved: int = 15
    refs_batch_size: int = 15
    refs_priority: list[str] = field(default_factory=list)

    # --- Paths ---

    @property
    def base_dir(self) -> Path:
        return CHARACTERS_DIR / self.slug

    @property
    def refs_dir(self) -> Path:
        return self.base_dir / "refs"

    @property
    def approved_refs_dir(self) -> Path:
        return self.base_dir / "refs" / "approved"

    @property
    def pending_refs_dir(self) -> Path:
        return self.base_dir / "refs" / "pending"

    @property
    def rejected_refs_dir(self) -> Path:
        return self.base_dir / "refs" / "rejected"

    @property
    def output_dir(self) -> Path:
        return self.base_dir / "output"

    @property
    def backgrounds_dir(self) -> Path:
        return self.base_dir / "output" / "backgrounds"

    @property
    def themes_path(self) -> Path:
        return self.base_dir / "themes.yaml"

    @property
    def config_path(self) -> Path:
        return self.base_dir / "character.yaml"

    # --- Refs helpers ---

    def approved_refs(self) -> list[Path]:
        """Lista imagens de referencia aprovadas."""
        if not self.approved_refs_dir.exists():
            return []
        exts = {".png", ".jpg", ".jpeg", ".webp"}
        return sorted(
            p for p in self.approved_refs_dir.iterdir()
            if p.suffix.lower() in exts
        )

    def pending_refs(self) -> list[Path]:
        """Lista imagens de referencia pendentes."""
        if not self.pending_refs_dir.exists():
            return []
        exts = {".png", ".jpg", ".jpeg", ".webp"}
        return sorted(
            p for p in self.pending_refs_dir.iterdir()
            if p.suffix.lower() in exts
        )

    def rejected_refs(self) -> list[Path]:
        """Lista imagens de referencia rejeitadas."""
        if not self.rejected_refs_dir.exists():
            return []
        exts = {".png", ".jpg", ".jpeg", ".webp"}
        return sorted(
            p for p in self.rejected_refs_dir.iterdir()
            if p.suffix.lower() in exts
        )

    def is_ready(self) -> bool:
        """Personagem tem refs suficientes para usar no pipeline."""
        return len(self.approved_refs()) >= self.refs_min_approved

    def refs_stats(self) -> dict:
        """Estatisticas de referencias."""
        return {
            "approved": len(self.approved_refs()),
            "pending": len(self.pending_refs()),
            "rejected": len(self.rejected_refs()),
            "min_required": self.refs_min_approved,
            "ideal": self.refs_ideal_approved,
            "is_ready": self.is_ready(),
        }

    # --- Themes ---

    def load_themes(self) -> list[dict]:
        """Carrega temas do personagem."""
        if not self.themes_path.exists():
            return []
        try:
            data = yaml.safe_load(self.themes_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"Erro ao carregar themes de {self.slug}: {e}")
            return []

    def themes_dict(self) -> dict[str, dict]:
        """Temas como dicionario key -> {acao, cenario}."""
        return {
            t["key"]: {"acao": t.get("acao", ""), "cenario": t.get("cenario", "")}
            for t in self.load_themes() if t.get("key")
        }

    def to_summary(self) -> dict:
        """Resumo para listagem (sem dados pesados)."""
        refs = self.refs_stats()
        avatar = None
        approved = self.approved_refs()
        if approved:
            avatar = approved[0].name
        return {
            "slug": self.slug,
            "name": self.name,
            "handle": self.handle,
            "status": self.status,
            "avatar": avatar,
            "refs": refs,
            "themes_count": len(self.load_themes()),
        }


# --- YAML Serialization ---

def _style_to_dict(style: CharacterStyle) -> dict:
    return {
        "overlay_color": list(style.overlay_color),
        "glow_color": list(style.glow_color),
        "text_color": list(style.text_color),
        "text_stroke_width": style.text_stroke_width,
        "text_vertical_position": style.text_vertical_position,
        "font_size": style.font_size,
        "watermark_color": list(style.watermark_color),
        "watermark_font_size": style.watermark_font_size,
    }


def _style_from_dict(data: dict) -> CharacterStyle:
    return CharacterStyle(
        overlay_color=tuple(data.get("overlay_color", [10, 10, 30, 40])),
        glow_color=tuple(data.get("glow_color", [255, 200, 80, 15])),
        text_color=tuple(data.get("text_color", [255, 255, 255])),
        text_stroke_width=data.get("text_stroke_width", 2),
        text_vertical_position=data.get("text_vertical_position", 0.80),
        font_size=data.get("font_size", 48),
        watermark_color=tuple(data.get("watermark_color", [200, 180, 130, 120])),
        watermark_font_size=data.get("watermark_font_size", 22),
    )


def _config_to_yaml(config: CharacterConfig) -> dict:
    """Converte CharacterConfig para dicionario YAML-serializavel."""
    return {
        "slug": config.slug,
        "name": config.name,
        "handle": config.handle,
        "watermark": config.watermark,
        "status": config.status,
        "persona": {
            "system_prompt": config.system_prompt,
            "humor_style": config.humor_style,
            "tone": config.tone,
            "catchphrases": config.catchphrases,
            "rules": {
                "max_chars": config.rules_max_chars,
                "forbidden": config.rules_forbidden,
            },
        },
        "visual": {
            "character_dna": config.character_dna,
            "negative_traits": config.negative_traits,
            "composition": config.composition,
        },
        "comfyui": {
            "trigger_word": config.comfyui_trigger_word,
            "character_dna": config.comfyui_character_dna,
            "lora_path": config.comfyui_lora_path,
        },
        "branding": {
            "branded_hashtags": config.branded_hashtags,
            "caption_prompt": config.caption_prompt,
        },
        "style": _style_to_dict(config.style),
        "refs_config": {
            "min_approved": config.refs_min_approved,
            "ideal_approved": config.refs_ideal_approved,
            "batch_size": config.refs_batch_size,
            "priority_refs": config.refs_priority,
        },
    }


def _config_from_yaml(data: dict) -> CharacterConfig:
    """Cria CharacterConfig a partir de dicionario YAML."""
    persona = data.get("persona", {})
    visual = data.get("visual", {})
    comfyui = data.get("comfyui", {})
    branding = data.get("branding", {})
    style_data = data.get("style", {})
    refs_cfg = data.get("refs_config", {})
    rules = persona.get("rules", {})

    return CharacterConfig(
        slug=data.get("slug", ""),
        name=data.get("name", ""),
        handle=data.get("handle", ""),
        watermark=data.get("watermark", ""),
        status=data.get("status", "draft"),
        system_prompt=persona.get("system_prompt", ""),
        humor_style=persona.get("humor_style", ""),
        tone=persona.get("tone", ""),
        catchphrases=persona.get("catchphrases", []),
        rules_max_chars=rules.get("max_chars", 120),
        rules_forbidden=rules.get("forbidden", []),
        character_dna=visual.get("character_dna", ""),
        negative_traits=visual.get("negative_traits", ""),
        composition=visual.get("composition", ""),
        comfyui_trigger_word=comfyui.get("trigger_word", ""),
        comfyui_character_dna=comfyui.get("character_dna", ""),
        comfyui_lora_path=comfyui.get("lora_path", ""),
        branded_hashtags=branding.get("branded_hashtags", []),
        caption_prompt=branding.get("caption_prompt", ""),
        style=_style_from_dict(style_data) if style_data else CharacterStyle(),
        refs_min_approved=refs_cfg.get("min_approved", 5),
        refs_ideal_approved=refs_cfg.get("ideal_approved", 15),
        refs_batch_size=refs_cfg.get("batch_size", 15),
        refs_priority=refs_cfg.get("priority_refs", []),
    )


# --- Public API ---

def create_character_dirs(slug: str) -> Path:
    """Cria estrutura de diretorios para um novo personagem."""
    base = CHARACTERS_DIR / slug
    (base / "refs" / "approved").mkdir(parents=True, exist_ok=True)
    (base / "refs" / "pending").mkdir(parents=True, exist_ok=True)
    (base / "refs" / "rejected").mkdir(parents=True, exist_ok=True)
    (base / "output" / "backgrounds").mkdir(parents=True, exist_ok=True)
    return base


def save_character(config: CharacterConfig) -> Path:
    """Salva CharacterConfig em character.yaml."""
    create_character_dirs(config.slug)
    data = _config_to_yaml(config)
    path = config.config_path
    path.write_text(
        yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    logger.info(f"Personagem salvo: {config.slug} ({path})")
    return path


def load_character(slug: str) -> CharacterConfig:
    """Carrega CharacterConfig de character.yaml."""
    path = CHARACTERS_DIR / slug / "character.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Personagem nao encontrado: {slug}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    config = _config_from_yaml(data)
    # Auto-update status baseado em refs
    if config.status == "refining" and config.is_ready():
        config.status = "ready"
    elif config.status == "ready" and not config.is_ready():
        config.status = "refining"
    return config


def list_characters() -> list[CharacterConfig]:
    """Lista todos os personagens disponiveis."""
    if not CHARACTERS_DIR.exists():
        return []
    characters = []
    for char_dir in sorted(CHARACTERS_DIR.iterdir()):
        config_path = char_dir / "character.yaml"
        if config_path.exists():
            try:
                characters.append(load_character(char_dir.name))
            except Exception as e:
                logger.warning(f"Erro ao carregar personagem {char_dir.name}: {e}")
    return characters


def delete_character(slug: str) -> bool:
    """Deleta um personagem e seus arquivos."""
    if slug == DEFAULT_CHARACTER:
        raise ValueError("Nao e possivel deletar o personagem padrao")
    char_dir = CHARACTERS_DIR / slug
    if not char_dir.exists():
        return False
    shutil.rmtree(char_dir)
    logger.info(f"Personagem deletado: {slug}")
    return True


def update_character(slug: str, updates: dict[str, Any]) -> CharacterConfig:
    """Atualiza campos de um personagem existente."""
    config = load_character(slug)
    data = _config_to_yaml(config)

    # Merge updates
    for key, value in updates.items():
        if key in data:
            if isinstance(data[key], dict) and isinstance(value, dict):
                data[key].update(value)
            else:
                data[key] = value
        else:
            # Campos top-level
            data[key] = value

    updated = _config_from_yaml(data)
    save_character(updated)
    return updated


def get_default_character() -> CharacterConfig:
    """Carrega o personagem padrao."""
    return load_character(DEFAULT_CHARACTER)


def slugify(text: str) -> str:
    """Expoe slugify para uso externo."""
    return _slugify(text)
