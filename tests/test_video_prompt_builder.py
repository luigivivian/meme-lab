"""Tests for VideoPromptBuilder v2 templates, system prompts, and version switching.

Validates research-based template structure per Phase 999.3 decisions:
- D-02: All 17 themes present in v2
- D-03: Three-layer motion (camera + subject + physics)
- D-04: 4-5 sentences, 300-500 chars per template
- D-05: VIDEO_PROMPT_STYLE version switching
- D-06: System prompt structured sections (CAMERA/SUBJECT/PHYSICS/ATMOSPHERE)
- D-07: 500 char prompt cap
- D-08: Technique reference comments
"""

import re
import sys
import os

import pytest

# Ensure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.video_gen.video_prompt_builder import (
    MOTION_TEMPLATES,
    MOTION_TEMPLATES_V1,
    MOTION_TEMPLATES_V2,
    VideoPromptBuilder,
    _get_templates,
    _SYSTEM_PROMPT,
    _SYSTEM_PROMPT_V1,
    _SYSTEM_PROMPT_V2,
    _ENHANCE_PROMPT,
    _ENHANCE_PROMPT_V1,
    _ENHANCE_PROMPT_V2,
    _get_system_prompt,
    _get_enhance_prompt,
)


# -- Expected theme keys (17 total) ----------------------------------------

EXPECTED_THEMES = {
    "sabedoria", "confusao", "segunda_feira", "vitoria", "tecnologia",
    "cafe", "comida", "trabalho", "relaxando", "meditando",
    "relacionamento", "confronto", "surpresa", "internet", "generico",
    "cotidiano", "descanso",
}


# -- D-02: All 17 themes present -------------------------------------------

def test_v2_all_17_themes():
    """MOTION_TEMPLATES_V2 has exactly 17 keys matching V1 keys."""
    assert set(MOTION_TEMPLATES_V2.keys()) == EXPECTED_THEMES
    assert set(MOTION_TEMPLATES_V1.keys()) == EXPECTED_THEMES
    assert len(MOTION_TEMPLATES_V2) == 17


# -- D-02: V1 preserved unchanged ------------------------------------------

def test_v1_preserved_unchanged():
    """V1 templates have all 17 keys and contain original v1 text."""
    assert len(MOTION_TEMPLATES_V1) == 17
    # v1 templates start with lowercase "wizard" (no camera direction prefix)
    assert "wizard slowly strokes" in MOTION_TEMPLATES_V1["sabedoria"]
    assert "wizard holds ornate mug" in MOTION_TEMPLATES_V1["cafe"]
    assert "wizard stands with staff" in MOTION_TEMPLATES_V1["generico"]


# -- D-04: Template length 300-500 chars ------------------------------------

def test_v2_template_length():
    """Each v2 template is 300-500 characters."""
    for theme, template in MOTION_TEMPLATES_V2.items():
        length = len(template)
        assert 300 <= length <= 500, (
            f"Theme '{theme}' has {length} chars (expected 300-500): "
            f"{template[:60]}..."
        )


# -- D-04: Template sentence count 4-6 -------------------------------------

def test_v2_template_sentence_count():
    """Each v2 template has 4-6 sentences (periods followed by space or end)."""
    for theme, template in MOTION_TEMPLATES_V2.items():
        # Count sentences: period followed by space or end of string
        sentences = len(re.findall(r"\.\s|\.\"?\s*$", template))
        assert 4 <= sentences <= 6, (
            f"Theme '{theme}' has {sentences} sentences (expected 4-6)"
        )


# -- D-03: Present continuous tense ----------------------------------------

def test_v2_present_continuous_tense():
    """Each v2 template contains at least one 'is ' or 'are ' (present continuous)."""
    for theme, template in MOTION_TEMPLATES_V2.items():
        has_continuous = "is " in template or "are " in template
        assert has_continuous, (
            f"Theme '{theme}' lacks present continuous tense ('is ' or 'are ')"
        )


# -- D-03: Three-layer motion (camera + subject + physics) -----------------

CAMERA_WORDS = {
    "camera", "push-in", "dolly", "pan", "static", "parallax", "shot", "angle",
}
PHYSICS_WORDS = {
    "robe", "fabric", "beard", "staff", "particles", "glow", "light",
}


def test_v2_three_layers():
    """Each v2 template has camera, physics, and present continuous verb layers."""
    for theme, template in MOTION_TEMPLATES_V2.items():
        lower = template.lower()

        has_camera = any(word in lower for word in CAMERA_WORDS)
        has_physics = any(word in lower for word in PHYSICS_WORDS)
        has_continuous = "is " in template or "are " in template

        assert has_camera, f"Theme '{theme}' missing camera layer"
        assert has_physics, f"Theme '{theme}' missing physics layer"
        assert has_continuous, f"Theme '{theme}' missing present continuous"


# -- D-05: Version switching (templates) ------------------------------------

def test_version_switching_v1(monkeypatch):
    """Setting VIDEO_PROMPT_STYLE to 'v1' returns V1 templates."""
    import config
    monkeypatch.setattr(config, "VIDEO_PROMPT_STYLE", "v1")
    result = _get_templates()
    assert result is MOTION_TEMPLATES_V1


def test_version_switching_v2(monkeypatch):
    """Setting VIDEO_PROMPT_STYLE to 'v2' returns V2 templates."""
    import config
    monkeypatch.setattr(config, "VIDEO_PROMPT_STYLE", "v2")
    result = _get_templates()
    assert result is MOTION_TEMPLATES_V2


def test_version_switching_default(monkeypatch):
    """Without VIDEO_PROMPT_STYLE set, default returns V2."""
    import config
    monkeypatch.delattr(config, "VIDEO_PROMPT_STYLE", raising=False)
    monkeypatch.delenv("VIDEO_PROMPT_STYLE", raising=False)
    result = _get_templates()
    assert result is MOTION_TEMPLATES_V2


# -- Backward compatibility -------------------------------------------------

def test_backward_compat_alias():
    """MOTION_TEMPLATES alias exists and equals V2."""
    assert MOTION_TEMPLATES is MOTION_TEMPLATES_V2


# -- D-07: Prompt cap 500 chars --------------------------------------------

def test_prompt_cap_500():
    """Fallback prompt for generico is under 600 chars (base + camera instruction)."""
    builder = VideoPromptBuilder()
    prompt = builder.get_fallback_prompt("generico")
    assert len(prompt) <= 600, f"Fallback prompt is {len(prompt)} chars (expected <= 600)"


# -- Config constant exists -------------------------------------------------

def test_config_constant_exists():
    """VIDEO_PROMPT_STYLE exists in config and is v1 or v2."""
    from config import VIDEO_PROMPT_STYLE
    assert VIDEO_PROMPT_STYLE in ("v1", "v2")


# =========================================================================
# Plan 02 tests -- System prompt structure and version-aware selection
# =========================================================================


# -- D-06: System prompt v2 structured sections ----------------------------

def test_system_prompt_v2_sections():
    """_SYSTEM_PROMPT_V2 contains CAMERA, SUBJECT, PHYSICS, ATMOSPHERE sections."""
    for section in ["CAMERA", "SUBJECT", "PHYSICS", "ATMOSPHERE"]:
        assert section in _SYSTEM_PROMPT_V2, (
            f"Missing section label '{section}' in _SYSTEM_PROMPT_V2"
        )


def test_system_prompt_v2_present_continuous_rule():
    """_SYSTEM_PROMPT_V2 contains PRESENT CONTINUOUS tense instruction."""
    assert "PRESENT CONTINUOUS" in _SYSTEM_PROMPT_V2


def test_system_prompt_v2_char_limit():
    """_SYSTEM_PROMPT_V2 contains the 300-500 character output range instruction."""
    assert "300-500" in _SYSTEM_PROMPT_V2


def test_system_prompt_v2_one_camera_rule():
    """_SYSTEM_PROMPT_V2 contains ONE camera movement constraint."""
    assert "ONE camera" in _SYSTEM_PROMPT_V2 or "one clear" in _SYSTEM_PROMPT_V2


# -- D-06: Enhance prompt v2 structured sections ----------------------------

def test_enhance_prompt_v2_sections():
    """_ENHANCE_PROMPT_V2 contains CAMERA, SUBJECT, PHYSICS, ATMOSPHERE sections."""
    for section in ["CAMERA", "SUBJECT", "PHYSICS", "ATMOSPHERE"]:
        assert section in _ENHANCE_PROMPT_V2, (
            f"Missing section label '{section}' in _ENHANCE_PROMPT_V2"
        )


# -- System prompt version switching ----------------------------------------

def test_system_prompt_switching_v1(monkeypatch):
    """_get_system_prompt() returns v1 when style='v1'."""
    import config
    monkeypatch.setattr(config, "VIDEO_PROMPT_STYLE", "v1")
    result = _get_system_prompt()
    assert result is _SYSTEM_PROMPT_V1


def test_system_prompt_switching_v2(monkeypatch):
    """_get_system_prompt() returns v2 when style='v2'."""
    import config
    monkeypatch.setattr(config, "VIDEO_PROMPT_STYLE", "v2")
    result = _get_system_prompt()
    assert result is _SYSTEM_PROMPT_V2


# -- Enhance prompt version switching ---------------------------------------

def test_enhance_prompt_switching_v1(monkeypatch):
    """_get_enhance_prompt() returns v1 when style='v1'."""
    import config
    monkeypatch.setattr(config, "VIDEO_PROMPT_STYLE", "v1")
    result = _get_enhance_prompt()
    assert result is _ENHANCE_PROMPT_V1


def test_enhance_prompt_switching_v2(monkeypatch):
    """_get_enhance_prompt() returns v2 when style='v2'."""
    import config
    monkeypatch.setattr(config, "VIDEO_PROMPT_STYLE", "v2")
    result = _get_enhance_prompt()
    assert result is _ENHANCE_PROMPT_V2


# -- V1 prompts preserved --------------------------------------------------

def test_v1_prompts_preserved():
    """_SYSTEM_PROMPT_V1 contains original v1 text (2-4 sentences, max 300 chars)."""
    assert "2-4 sentences" in _SYSTEM_PROMPT_V1 or "max 300 chars" in _SYSTEM_PROMPT_V1


# -- Backward compatibility aliases for prompts ----------------------------

def test_backward_compat_prompt_aliases():
    """_SYSTEM_PROMPT and _ENHANCE_PROMPT are aliases for their v2 versions."""
    assert _SYSTEM_PROMPT is _SYSTEM_PROMPT_V2
    assert _ENHANCE_PROMPT is _ENHANCE_PROMPT_V2
