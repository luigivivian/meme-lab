"""Conversores entre ORM models e dataclasses existentes."""

from src.characters import CharacterConfig, CharacterStyle, _style_from_dict, _style_to_dict
from src.database.models import Character as CharacterORM


def orm_to_character_config(orm: CharacterORM) -> CharacterConfig:
    """Converte Character ORM para CharacterConfig dataclass."""
    style_data = orm.style or {}
    return CharacterConfig(
        slug=orm.slug,
        name=orm.name,
        handle=orm.handle or "",
        watermark=orm.watermark or "",
        status=orm.status or "draft",
        system_prompt=orm.system_prompt or "",
        humor_style=orm.humor_style or "",
        tone=orm.tone or "",
        catchphrases=orm.catchphrases or [],
        rules_max_chars=orm.rules_max_chars or 120,
        rules_forbidden=orm.rules_forbidden or [],
        character_dna=orm.character_dna or "",
        negative_traits=orm.negative_traits or "",
        composition=orm.composition or "",
        comfyui_trigger_word=orm.comfyui_trigger_word or "",
        comfyui_character_dna=orm.comfyui_character_dna or "",
        comfyui_lora_path=orm.comfyui_lora_path or "",
        branded_hashtags=orm.branded_hashtags or [],
        caption_prompt=orm.caption_prompt or "",
        style=_style_from_dict(style_data) if style_data else CharacterStyle(),
        refs_min_approved=orm.refs_min_approved or 5,
        refs_ideal_approved=orm.refs_ideal_approved or 15,
        refs_batch_size=orm.refs_batch_size or 15,
        refs_priority=orm.refs_priority or [],
    )


def character_config_to_orm_dict(config: CharacterConfig) -> dict:
    """Converte CharacterConfig dataclass para dict compativel com ORM."""
    return {
        "slug": config.slug,
        "name": config.name,
        "handle": config.handle,
        "watermark": config.watermark,
        "status": config.status,
        "system_prompt": config.system_prompt,
        "humor_style": config.humor_style,
        "tone": config.tone,
        "catchphrases": config.catchphrases,
        "rules_max_chars": config.rules_max_chars,
        "rules_forbidden": config.rules_forbidden,
        "character_dna": config.character_dna,
        "negative_traits": config.negative_traits,
        "composition": config.composition,
        "comfyui_trigger_word": config.comfyui_trigger_word,
        "comfyui_character_dna": config.comfyui_character_dna,
        "comfyui_lora_path": config.comfyui_lora_path,
        "branded_hashtags": config.branded_hashtags,
        "caption_prompt": config.caption_prompt,
        "style": _style_to_dict(config.style),
        "refs_min_approved": config.refs_min_approved,
        "refs_ideal_approved": config.refs_ideal_approved,
        "refs_batch_size": config.refs_batch_size,
        "refs_priority": config.refs_priority,
    }


def api_create_to_orm_dict(data: dict, slug: str) -> dict:
    """Converte dados do CharacterCreateRequest da API para dict ORM."""
    persona = data.get("persona", {})
    visual = data.get("visual", {})
    comfyui = data.get("comfyui", {})
    branding = data.get("branding", {})
    style = data.get("style", {})
    rules = persona.get("rules", {})

    return {
        "slug": slug,
        "name": data.get("name", ""),
        "handle": data.get("handle", ""),
        "watermark": data.get("watermark", "") or data.get("handle", ""),
        "status": "draft",
        "system_prompt": persona.get("system_prompt", ""),
        "humor_style": persona.get("humor_style", ""),
        "tone": persona.get("tone", ""),
        "catchphrases": persona.get("catchphrases", []),
        "rules_max_chars": rules.get("max_chars", 120),
        "rules_forbidden": rules.get("forbidden", []),
        "character_dna": visual.get("character_dna", ""),
        "negative_traits": visual.get("negative_traits", ""),
        "composition": visual.get("composition", ""),
        "rendering": visual.get("rendering", {}),
        "comfyui_trigger_word": comfyui.get("trigger_word", ""),
        "comfyui_character_dna": comfyui.get("character_dna", ""),
        "comfyui_lora_path": comfyui.get("lora_path", ""),
        "branded_hashtags": branding.get("branded_hashtags", []),
        "caption_prompt": branding.get("caption_prompt", ""),
        "style": style if style else {},
        "refs_min_approved": 5,
        "refs_ideal_approved": 15,
        "refs_batch_size": 15,
        "refs_priority": [],
    }


def api_update_to_orm_dict(data: dict) -> dict:
    """Converte dados do CharacterUpdateRequest para campos flat do ORM."""
    result = {}

    # Campos top-level
    for key in ["name", "handle", "watermark", "status"]:
        if key in data and data[key] is not None:
            result[key] = data[key]

    # Persona (nested → flat)
    persona = data.get("persona")
    if persona and isinstance(persona, dict):
        if "system_prompt" in persona:
            result["system_prompt"] = persona["system_prompt"]
        if "humor_style" in persona:
            result["humor_style"] = persona["humor_style"]
        if "tone" in persona:
            result["tone"] = persona["tone"]
        if "catchphrases" in persona:
            result["catchphrases"] = persona["catchphrases"]
        rules = persona.get("rules")
        if rules and isinstance(rules, dict):
            if "max_chars" in rules:
                result["rules_max_chars"] = rules["max_chars"]
            if "forbidden" in rules:
                result["rules_forbidden"] = rules["forbidden"]

    # Visual (nested → flat)
    visual = data.get("visual")
    if visual and isinstance(visual, dict):
        if "character_dna" in visual:
            result["character_dna"] = visual["character_dna"]
        if "negative_traits" in visual:
            result["negative_traits"] = visual["negative_traits"]
        if "composition" in visual:
            result["composition"] = visual["composition"]
        if "rendering" in visual:
            result["rendering"] = visual["rendering"]

    # ComfyUI (nested → flat)
    comfyui = data.get("comfyui")
    if comfyui and isinstance(comfyui, dict):
        if "trigger_word" in comfyui:
            result["comfyui_trigger_word"] = comfyui["trigger_word"]
        if "character_dna" in comfyui:
            result["comfyui_character_dna"] = comfyui["character_dna"]
        if "lora_path" in comfyui:
            result["comfyui_lora_path"] = comfyui["lora_path"]

    # Branding (nested → flat)
    branding = data.get("branding")
    if branding and isinstance(branding, dict):
        if "branded_hashtags" in branding:
            result["branded_hashtags"] = branding["branded_hashtags"]
        if "caption_prompt" in branding:
            result["caption_prompt"] = branding["caption_prompt"]

    # Style (JSON inteiro)
    style = data.get("style")
    if style and isinstance(style, dict):
        result["style"] = style

    # Refs config
    refs_config = data.get("refs_config")
    if refs_config and isinstance(refs_config, dict):
        if "min_approved" in refs_config:
            result["refs_min_approved"] = refs_config["min_approved"]
        if "ideal_approved" in refs_config:
            result["refs_ideal_approved"] = refs_config["ideal_approved"]
        if "batch_size" in refs_config:
            result["refs_batch_size"] = refs_config["batch_size"]
        if "priority_refs" in refs_config:
            result["refs_priority"] = refs_config["priority_refs"]

    return result
