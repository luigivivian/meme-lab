"""Seed — migra dados existentes (YAML + filesystem) para o SQLite.

Uso:
    python -m src.database.seed

Idempotente: pode rodar varias vezes sem duplicar dados.
"""

import asyncio
import os
from pathlib import Path

import yaml

from config import BASE_DIR
from src.database.session import get_session_factory, init_db
from src.database.models import Character, CharacterRef, Theme


CHARACTERS_DIR = BASE_DIR / "characters"
GLOBAL_THEMES_PATH = BASE_DIR / "config" / "themes.yaml"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

# 13 situacoes built-in do gemini_client.py
BUILTIN_SITUACOES = {
    "sabedoria": ("wise elderly wizard contemplating ancient knowledge with a serene expression", "mystical library with floating books and glowing orbs"),
    "confusao": ("confused elderly wizard scratching head with bewildered expression", "chaotic magical laboratory with bubbling potions and sparks"),
    "segunda_feira": ("tired elderly wizard struggling to wake up, holding magical staff for support", "cozy wizard bedroom at dawn with alarm clock and scattered spell books"),
    "vitoria": ("triumphant elderly wizard celebrating with raised staff, magical sparks flying", "epic mountain peak at sunset with dramatic clouds"),
    "tecnologia": ("curious elderly wizard examining a glowing smartphone with amazement", "modern tech office merged with medieval magical elements"),
    "cafe": ("elderly wizard lovingly holding an oversized magical coffee cup with steam swirls", "cozy tavern corner with morning light and spell ingredients"),
    "comida": ("hungry elderly wizard eyeing a massive feast with wide eyes and drooling", "grand medieval dining hall with magical floating platters"),
    "trabalho": ("exhausted elderly wizard drowning in scrolls and paperwork at a desk", "cluttered wizard office with stacked books and a broken hourglass"),
    "relaxando": ("peaceful elderly wizard lounging in a magical hammock with eyes half-closed", "serene enchanted forest clearing with fireflies and gentle stream"),
    "meditando": ("elderly wizard in deep meditation floating slightly above ground", "zen garden with bonsai trees and mystical fog"),
    "relacionamento": ("elderly wizard with a knowing smirk giving romantic advice", "romantic moonlit balcony overlooking a magical cityscape"),
    "confronto": ("defiant elderly wizard standing firm with glowing eyes and raised staff", "dramatic stormy battlefield with lightning and magical barriers"),
    "surpresa": ("shocked elderly wizard with jaw dropped and hat flying off", "portal room with unexpected magical creatures emerging"),
}


def _load_yaml(path: Path) -> list[dict] | dict | None:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"  WARN: Erro ao ler {path}: {e}")
        return None


def _parse_character_yaml(data: dict) -> dict:
    """Converte YAML de character para dict compativel com ORM."""
    persona = data.get("persona", {})
    visual = data.get("visual", {})
    comfyui = data.get("comfyui", {})
    branding = data.get("branding", {})
    style_data = data.get("style", {})
    refs_config = data.get("refs_config", {})
    rules = persona.get("rules", {})

    return {
        "slug": data.get("slug", ""),
        "name": data.get("name", ""),
        "handle": data.get("handle", ""),
        "watermark": data.get("watermark", ""),
        "status": data.get("status", "draft"),
        # Persona
        "system_prompt": persona.get("system_prompt", ""),
        "humor_style": persona.get("humor_style", ""),
        "tone": persona.get("tone", ""),
        "catchphrases": persona.get("catchphrases", []),
        "rules_max_chars": rules.get("max_chars", 120),
        "rules_forbidden": rules.get("forbidden", []),
        # Visual
        "character_dna": visual.get("character_dna", ""),
        "negative_traits": visual.get("negative_traits", ""),
        "composition": visual.get("composition", ""),
        # ComfyUI
        "comfyui_trigger_word": comfyui.get("trigger_word", ""),
        "comfyui_character_dna": comfyui.get("character_dna", ""),
        "comfyui_lora_path": comfyui.get("lora_path", ""),
        # Branding
        "branded_hashtags": branding.get("branded_hashtags", []),
        "caption_prompt": branding.get("caption_prompt", ""),
        # Style (serializado como JSON)
        "style": style_data,
        # Refs config
        "refs_min_approved": refs_config.get("min_approved", 5),
        "refs_ideal_approved": refs_config.get("ideal_approved", 15),
        "refs_batch_size": refs_config.get("batch_size", 15),
        "refs_priority": refs_config.get("priority_refs", []),
    }


async def seed_characters(session):
    """Migra characters YAML para o banco."""
    from sqlalchemy import select

    if not CHARACTERS_DIR.exists():
        print("  Nenhum diretorio characters/ encontrado.")
        return

    for char_dir in sorted(CHARACTERS_DIR.iterdir()):
        if not char_dir.is_dir():
            continue
        yaml_path = char_dir / "character.yaml"
        if not yaml_path.exists():
            continue

        slug = char_dir.name
        existing = await session.execute(
            select(Character).where(Character.slug == slug)
        )
        if existing.scalar_one_or_none():
            print(f"  [SKIP] Character '{slug}' ja existe no banco.")
            continue

        data = _load_yaml(yaml_path)
        if not data:
            continue

        char_data = _parse_character_yaml(data)
        character = Character(**char_data)
        session.add(character)
        await session.flush()
        print(f"  [OK] Character '{slug}' migrado (id={character.id}).")

        # Migrar refs
        refs_dir = char_dir / "refs"
        if refs_dir.exists():
            for status_dir_name in ["approved", "pending", "rejected"]:
                status_dir = refs_dir / status_dir_name
                if not status_dir.exists():
                    continue
                count = 0
                for img_file in sorted(status_dir.iterdir()):
                    if img_file.suffix.lower() not in IMAGE_EXTENSIONS:
                        continue
                    ref = CharacterRef(
                        character_id=character.id,
                        filename=img_file.name,
                        status=status_dir_name,
                        file_path=str(img_file.relative_to(BASE_DIR)),
                        file_size_bytes=img_file.stat().st_size if img_file.exists() else None,
                        source="generated",
                    )
                    session.add(ref)
                    count += 1
                if count > 0:
                    print(f"    [OK] {count} refs '{status_dir_name}' migradas.")
        await session.flush()


async def seed_themes(session):
    """Migra themes YAML (globais + por character) para o banco."""
    from sqlalchemy import select

    # 1. Builtin themes (13 SITUACOES)
    for key, (acao, cenario) in BUILTIN_SITUACOES.items():
        existing = await session.execute(
            select(Theme).where(
                Theme.key == key, Theme.character_id.is_(None), Theme.is_builtin == True  # noqa: E712
            )
        )
        if existing.scalar_one_or_none():
            continue
        theme = Theme(
            character_id=None,
            key=key,
            label=key.replace("_", " ").title(),
            acao=acao,
            cenario=cenario,
            is_builtin=True,
        )
        session.add(theme)
    await session.flush()
    print(f"  [OK] {len(BUILTIN_SITUACOES)} temas built-in verificados.")

    # 2. Global themes (config/themes.yaml)
    global_themes = _load_yaml(GLOBAL_THEMES_PATH)
    if global_themes and isinstance(global_themes, list):
        count = 0
        for t in global_themes:
            key = t.get("key", "")
            if not key:
                continue
            existing = await session.execute(
                select(Theme).where(
                    Theme.key == key, Theme.character_id.is_(None)
                )
            )
            if existing.scalar_one_or_none():
                continue
            theme = Theme(
                character_id=None,
                key=key,
                label=t.get("label", ""),
                acao=t.get("acao", ""),
                cenario=t.get("cenario", ""),
                count=t.get("count", 1),
                is_builtin=False,
            )
            session.add(theme)
            count += 1
        await session.flush()
        print(f"  [OK] {count} temas globais migrados de config/themes.yaml.")

    # 3. Themes por character
    if not CHARACTERS_DIR.exists():
        return

    for char_dir in sorted(CHARACTERS_DIR.iterdir()):
        if not char_dir.is_dir():
            continue
        themes_path = char_dir / "themes.yaml"
        if not themes_path.exists():
            continue

        slug = char_dir.name
        char_result = await session.execute(
            select(Character).where(Character.slug == slug)
        )
        character = char_result.scalar_one_or_none()
        if not character:
            continue

        char_themes = _load_yaml(themes_path)
        if not char_themes or not isinstance(char_themes, list):
            continue

        count = 0
        for t in char_themes:
            key = t.get("key", "")
            if not key:
                continue
            existing = await session.execute(
                select(Theme).where(
                    Theme.key == key, Theme.character_id == character.id
                )
            )
            if existing.scalar_one_or_none():
                continue
            theme = Theme(
                character_id=character.id,
                key=key,
                label=t.get("label", ""),
                acao=t.get("acao", ""),
                cenario=t.get("cenario", ""),
                count=t.get("count", 1),
                is_builtin=False,
            )
            session.add(theme)
            count += 1
        await session.flush()
        if count > 0:
            print(f"  [OK] {count} temas migrados para '{slug}'.")


async def run_seed():
    """Executa o seed completo."""
    print("=== Clip-Flow Database Seed ===\n")

    # Garante que o diretorio data/ existe
    db_dir = BASE_DIR / "data"
    db_dir.mkdir(exist_ok=True)

    # Cria tabelas
    print("[1/3] Criando tabelas...")
    await init_db()
    print("  [OK] Tabelas criadas.\n")

    factory = get_session_factory()
    async with factory() as session:
        # Migra characters + refs
        print("[2/3] Migrando characters e refs...")
        await seed_characters(session)
        print()

        # Migra themes
        print("[3/3] Migrando themes...")
        await seed_themes(session)
        print()

        await session.commit()

    print("=== Seed concluido com sucesso! ===")


if __name__ == "__main__":
    asyncio.run(run_seed())
