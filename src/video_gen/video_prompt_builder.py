"""VideoPromptBuilder -- generates LLM-powered motion prompts for Kie.ai Sora 2.

Per D-02: Each video gets a unique motion prompt from Gemini, tailored to theme/pose/scene.
Per D-03: video_prompt_notes per theme accumulate learnings (e.g., "avoid fast camera").
The LLM reads these notes when generating prompts, creating an iterative improvement loop.

Per D-01: Videos use the raw background image (no text/watermark). Text is added later by FFmpeg in Phase 999.2.
"""

import logging
import os

logger = logging.getLogger("clip-flow.video_prompt_builder")

# -- Original v1 templates -- preserved for fallback (per D-05) ----------
# Base motion descriptions used as LLM context, NOT as final prompts.
# Keys match SCENE_TEMPLATES in src/image_gen/prompt_builder.py.

MOTION_TEMPLATES_V1: dict[str, str] = {
    "sabedoria": (
        "The wizard slowly strokes his long beard with one hand, head nodding gently. "
        "His other hand grips the staff as the crystal tip pulses with blue glow. "
        "Robes sway with his breathing, magical particles drift upward around him."
    ),
    "confusao": (
        "The wizard tilts his head side to side in confusion, eyebrows furrowing. "
        "He shifts his weight between feet, one hand scratches under his hat. "
        "His staff wobbles slightly in his grip, small sparkles pop around his head."
    ),
    "segunda_feira": (
        "The wizard raises a coffee goblet to his lips with both hands, sipping slowly. "
        "His eyes droop heavily then snap open with a blink. His shoulders slump, "
        "chest rises with a deep sigh. Steam curls from the mug with golden sparkles."
    ),
    "vitoria": (
        "The wizard thrusts his staff upward triumphantly, arm fully extended. "
        "His body leans back with the motion, robes billow outward. "
        "He pumps his fist, beard swaying with the celebration. Golden particles erupt."
    ),
    "tecnologia": (
        "The wizard leans forward curiously, poking at a glowing crystal with one finger. "
        "His head tilts, eyes widen, then he pulls back startled. "
        "His hat shifts as he scratches his head in bewilderment. Digital runes flicker."
    ),
    "cafe": (
        "The wizard cradles an ornate mug with both hands, bringing it close to inhale the steam. "
        "He takes a long sip, eyes closing contentedly. His chest expands with a satisfied breath, "
        "shoulders relaxing down. Magical sparkles rise from the mug."
    ),
    "comida": (
        "The wizard stirs a bubbling cauldron with a large ladle, leaning in to smell. "
        "He tastes from the ladle, eyes rolling with delight. His free hand gestures approvingly, "
        "beard swinging with his animated movements. Colorful vapors swirl."
    ),
    "trabalho": (
        "The wizard hunches over parchment, quill moving rapidly in his hand. "
        "He pauses, looks up thinking, then returns to writing with intensity. "
        "His other hand taps the desk impatiently. Ink trails transform into floating runes."
    ),
    "relaxando": (
        "The wizard reclines in a chair, arms crossed over his chest. His hat slowly tips "
        "over his eyes. His chest rises and falls with deep, slow breaths. "
        "One hand dangles limply, fingers twitching. Staff leans nearby, glowing faintly."
    ),
    "meditando": (
        "The wizard sits cross-legged, hands resting on knees, palms up. "
        "His chest rises slowly with deep breathing, robes settling with each exhale. "
        "His head tilts slightly upward, a serene expression. Blue-gold aura pulses outward."
    ),
    "relacionamento": (
        "The wizard holds a glowing heart crystal between both hands, turning it gently. "
        "He looks at it with a knowing smile, then glances up warmly. "
        "His shoulders shift as he brings the crystal closer to his chest. Pink aura flows."
    ),
    "confronto": (
        "The wizard plants his staff firmly on the ground, both hands gripping tight. "
        "He steps forward with one foot, robes whipping in dramatic wind. "
        "His jaw clenches, eyes narrow with determination. Golden energy crackles from the staff tip."
    ),
    "surpresa": (
        "The wizard jolts backward, eyes going wide, hat flying up from his head briefly. "
        "Both hands shoot up in shock, fingers splayed. He stumbles back half a step, "
        "then catches himself on his staff. Sparkles burst around him."
    ),
    "internet": (
        "The wizard peers into a glowing crystal ball, leaning in close. "
        "His expression shifts from curiosity to surprise to amusement rapidly. "
        "One hand waves dismissively, the other adjusts his hat. Blue light dances on his face."
    ),
    "generico": (
        "The wizard shifts his weight, adjusting his grip on the staff. "
        "He looks around slowly, beard swaying with the head turn. "
        "His chest rises with a calm breath, robes flowing gently. "
        "The crystal tip pulses with rhythmic magical glow, particles drift."
    ),
    "cotidiano": (
        "The wizard leans casually on his staff, crossing one ankle over the other. "
        "He raises an ale mug for a relaxed sip, then wipes his beard with his sleeve. "
        "His body sways slightly, easy posture. Faint sparkles drift around."
    ),
    "descanso": (
        "The wizard sleeps in a wooden chair, head nodding forward and catching himself. "
        "His chest rises and falls with slow breaths, hat drooping over his eyes. "
        "One hand twitches in his lap. Soft blue particles float around peacefully."
    ),
}


# -- v2 templates -- Three-layer motion framework (OpenAI Cookbook + awesome-sora2) --
# Each template: 4-5 sentences, 300-500 chars
# Structure: [Camera macro] + [Subject primary + micro] + [Physics/atmosphere]
# Tense: present continuous throughout ("is raising", "are drifting")
# Source: OpenAI Sora 2 Prompting Guide + WaveSpeedAI + awesome-sora2 community

MOTION_TEMPLATES_V2: dict[str, str] = {
    # Camera: slow push-in -- contemplative theme benefits from gradual intimacy
    "sabedoria": (
        "Slow push-in from medium shot. "
        "The wizard is gently stroking his long beard with one hand, head nodding slowly in contemplation. "
        "His staff crystal is pulsing with a steady warm glow as his chest rises with calm breathing. "
        "Robes are swaying softly with each breath, magical particles are drifting upward, "
        "warm golden rim light is catching the fabric edges."
    ),
    # Camera: static with subtle instability -- mirrors the confused state
    "confusao": (
        "Static camera with subtle instability. "
        "The wizard is tilting his head side to side, eyebrows furrowing with bewilderment. "
        "One hand is scratching under his hat while the other grips the staff for balance. "
        "The staff is wobbling slightly, small sparkles are popping erratically around him, "
        "robe fabric is shifting with each confused weight change."
    ),
    # Camera: very slow push-in -- sleepy drift pace for Monday mood
    "segunda_feira": (
        "Very slow push-in with drowsy drift pace. "
        "The wizard is raising a coffee goblet with both hands, sipping slowly with heavy eyelids. "
        "His eyes are drooping then snapping open, head nodding forward and catching itself. "
        "Steam is curling upward from the goblet with faint golden sparkles, "
        "heavy robe fabric is draping loosely over his tired shoulders."
    ),
    # Camera: slow dolly forward -- dynamic movement matches triumph energy
    "vitoria": (
        "Slow dolly forward toward the wizard. "
        "The wizard is thrusting his staff upward triumphantly, body leaning back with exertion. "
        "His robes are billowing outward dramatically with the force of the gesture. "
        "Golden particles are erupting from the staff tip in a burst, "
        "fabric is whipping with the upward motion, warm golden light is radiating outward."
    ),
    # Camera: static with glow-lit parallax -- tech theme with screen-like glow
    "tecnologia": (
        "Static camera with glow-lit parallax from the crystal device. "
        "The wizard is leaning forward, poking a glowing crystal with one curious finger. "
        "His head is tilting with widening eyes as digital runes are flickering around the device. "
        "Pointed hat fabric is shifting with his head movement, "
        "cool blue light is dancing across his face and beard."
    ),
    # Camera: slow push-in -- warm intimate framing for cozy theme
    "cafe": (
        "Slow push-in from medium shot. "
        "The wizard is cradling an ornate mug with both hands, bringing it close to inhale the steam. "
        "His eyes are closing contentedly, chest expanding with a deep satisfied breath. "
        "Warm steam is curling upward with faint golden sparkles, "
        "robe sleeves are draping softly over his wrists, soft warm rim light on his face."
    ),
    # Camera: gentle dolly forward -- draws viewer into the cauldron scene
    "comida": (
        "Gentle dolly forward toward the bubbling cauldron. "
        "The wizard is stirring with a large ladle, leaning in to smell the rising vapors. "
        "His free hand is gesturing approvingly as colorful steam swirls upward. "
        "Heavy robe fabric is swaying with his animated stirring movements, "
        "warm flickering light from the cauldron is casting dancing shadows."
    ),
    # Camera: static with desk parallax -- subtle depth from desk objects
    "trabalho": (
        "Static camera with subtle parallax from desk objects. "
        "The wizard is hunching over parchment, quill moving rapidly across the page. "
        "He is pausing to look up and think, then returning to write with renewed focus. "
        "Ink trails are transforming into tiny floating runes, "
        "robe sleeve is brushing the parchment edge with each stroke."
    ),
    # Camera: static with gentle parallax -- calm scene needs minimal movement
    "relaxando": (
        "Static camera with gentle parallax from nearby furniture. "
        "The wizard is reclining in a chair, hat slowly tipping over his eyes. "
        "His chest is rising and falling with deep slow breaths, fingers twitching in his lap. "
        "The staff is glowing faintly nearby, "
        "soft ambient particles are drifting lazily in the warm light."
    ),
    # Camera: static locked-off with subtle depth shift -- emphasizes stillness
    "meditando": (
        "Static locked-off camera with subtle depth shift. "
        "The wizard is sitting cross-legged, chest rising slowly with deep rhythmic breathing. "
        "His robes are settling gently with each exhale, hands resting on his knees. "
        "A blue-gold aura is pulsing rhythmically outward from his body, "
        "luminous particles are ascending slowly in the still air."
    ),
    # Camera: very slow push-in -- intimate framing for emotional theme
    "relacionamento": (
        "Very slow push-in with intimate framing. "
        "The wizard is holding a glowing heart crystal, turning it gently between his fingers. "
        "He is looking at it with a knowing smile, eyes softening with warmth. "
        "A pink aura is flowing between his hands, "
        "robe fabric is shifting with his gentle arm movements, soft warm light pulsing."
    ),
    # Camera: subtle push-in low angle -- dramatic power framing
    "confronto": (
        "Subtle push-in from low angle. "
        "The wizard is planting his staff firmly on the ground, both hands gripping tight. "
        "He is stepping forward with determination, robes whipping in a dramatic wind. "
        "Golden energy is crackling from the staff tip, "
        "heavy fabric is billowing with force, dust particles swirling at his feet."
    ),
    # Camera: static with slight shake -- mirrors the shock reaction
    "surpresa": (
        "Static camera with slight shake on the reaction beat. "
        "The wizard is jolting backward with wide eyes, his hat flying up briefly from the shock. "
        "His hands are shooting up in surprise, body recoiling and weight shifting backward. "
        "Bright sparkles are bursting around his head in a flash, "
        "heavy robe fabric is swinging with the sudden startled movement."
    ),
    # Camera: static with screen-glow parallax -- light from crystal creates depth
    "internet": (
        "Static camera with screen-glow parallax on the face. "
        "The wizard is peering into a glowing crystal ball, leaning in close with curiosity. "
        "His expression is shifting from curiosity to amusement, eyebrows rising. "
        "Blue light is dancing across his face, "
        "his long beard is catching the reflected glow, faint sparkles drifting."
    ),
    # Camera: slow push-in -- versatile default with gentle movement
    "generico": (
        "Slow push-in from medium shot. "
        "The wizard is shifting his weight slowly, adjusting his grip on the staff. "
        "He is looking around with calm awareness, beard swaying with his head movement. "
        "The crystal tip is pulsing with a rhythmic golden glow, "
        "robes are flowing gently, ambient particles are drifting in the light."
    ),
    # Camera: static with gentle ambient drift -- casual everyday feel
    "cotidiano": (
        "Static camera with gentle ambient drift. "
        "The wizard is leaning casually on his staff, one ankle crossing the other lazily. "
        "He is raising an ale mug for a relaxed sip, body swaying slightly with the motion. "
        "Faint sparkles are drifting lazily around him, "
        "robe fabric is settling with his casual posture, warm ambient light glowing softly."
    ),
    # Camera: static with very slow push-in -- peaceful sleeping scene
    "descanso": (
        "Static camera with very slow push-in. "
        "The wizard is sleeping in a wooden chair, head nodding forward gently. "
        "His chest is rising and falling with slow peaceful breaths, hand twitching in his lap. "
        "His hat is drooping over his eyes, soft blue particles are floating peacefully, "
        "robe fabric is draped loosely over the armrest."
    ),
}

# Backward compatibility alias -- external code importing MOTION_TEMPLATES gets v2
MOTION_TEMPLATES = MOTION_TEMPLATES_V2


# Per D-05: Version switching via VIDEO_PROMPT_STYLE env var
def _get_templates() -> dict[str, str]:
    """Return active template set based on VIDEO_PROMPT_STYLE config.

    Per D-05: v1 returns original templates, v2 returns researched patterns.
    Default: v2 (Sora 2 prompt engineering from OpenAI Cookbook + awesome-sora2).
    """
    try:
        from config import VIDEO_PROMPT_STYLE
        style = VIDEO_PROMPT_STYLE
    except (ImportError, AttributeError):
        style = os.getenv("VIDEO_PROMPT_STYLE", "v2")

    if style == "v1":
        return MOTION_TEMPLATES_V1
    return MOTION_TEMPLATES_V2


# -- System prompt for LLM ------------------------------------------------
# v2 structured prompt -- Three-layer motion framework (OpenAI Cookbook + awesome-sora2)
# Sections: Camera / Subject / Physics / Atmosphere (per D-06)

_SYSTEM_PROMPT_V1 = (
    "You generate SHORT motion/animation prompts for Sora 2 image-to-video AI. "
    "You receive an image of a cartoon wizard character and must describe the animation.\n\n"
    "CRITICAL RULES:\n"
    "- Output ONLY the motion prompt (2-4 sentences, max 300 chars)\n"
    "- CHARACTER MUST MOVE: describe specific body movements — head turning, arms gesturing, "
    "hands gripping staff tighter, shoulders shifting, beard swaying, eyes blinking or looking around, "
    "chest rising with breath, weight shifting between feet, robes flowing with body motion\n"
    "- CHARACTER is the PRIMARY subject of animation — background is secondary\n"
    "- Background: add ambient motion (particles, wind, light shifts) but keep the SAME scene\n"
    "- Camera: static or very slow push-in. NO fast zooms, NO cuts\n"
    "- NO speech, NO dialogue, NO lip movement, NO text, NO words appearing\n"
    "- NO scene changes, NO new objects, NO dramatic lighting changes\n"
    "- Keep the cartoon cel-shading art style\n"
    "- Portrait 4:5 aspect ratio\n"
    "- NEVER describe character appearance (already in the image)\n"
    "- Think: the character COMES ALIVE — natural idle animation like a video game character waiting"
)

# v2 structured prompt — Three-layer motion framework (OpenAI Cookbook + awesome-sora2)
_SYSTEM_PROMPT_V2 = (
    "You generate motion prompts for Sora 2 image-to-video AI. "
    "You receive context about a wizard character meme and must describe the MOTION and CAMERA movement.\n\n"
    "OUTPUT FORMAT (4-5 sentences, 300-500 chars):\n"
    "1. CAMERA: One clear camera movement (static, slow push-in, gentle dolly, subtle parallax)\n"
    "2. SUBJECT: Primary character animation in present continuous tense "
    "(is raising, is turning, are gripping). Include micro-actions: breathing, blinking, weight shifts\n"
    "3. PHYSICS: Cloth behavior (robes swaying, beard flowing), particle effects, material interactions\n"
    "4. ATMOSPHERE: Lighting shifts, ambient motion (wind, sparkles, glow pulses)\n\n"
    "RULES:\n"
    "- Use PRESENT CONTINUOUS tense (is walking, are floating, is glowing)\n"
    "- ONE camera movement per prompt -- do not combine pan + zoom + track\n"
    "- CHARACTER is primary subject -- background is secondary ambient\n"
    "- Describe motion in beats: initial state -> peak action -> settling\n"
    "- Include material descriptors: 'heavy robe fabric', 'wooden staff'\n"
    "- NO speech, NO dialogue, NO text, NO lip movement\n"
    "- NO scene changes, NO new objects appearing\n"
    "- Maintain cartoon cel-shading art style\n"
    "- Portrait 4:5 aspect ratio\n"
    "- NEVER describe character appearance (already in the image)"
)

_ENHANCE_PROMPT = (
    "You are a prompt engineer for Sora 2 image-to-video AI. "
    "The user described how they want a cartoon wizard character animated. Enhance it.\n\n"
    "RULES:\n"
    "- Keep the user's INTENT but make it technically precise for Sora 2\n"
    "- Output 2-4 sentences, max 500 chars\n"
    "- CHARACTER MUST BE THE FOCUS of animation — body, arms, head, expressions\n"
    "- Use PRESENT CONTINUOUS tense for motion descriptions\n"
    "- Add specific body mechanics: breathing, weight shift, gesture follow-through\n"
    "- Add ambient effects: particles, cloth physics, hair/beard sway\n"
    "- Camera: static or slow push-in\n"
    "- PRESERVE: original background, scene, art style — NO changes\n"
    "- NO speech, NO lip movement, NO text\n"
    "- Output ONLY the enhanced prompt, nothing else"
)


def _get_system_prompt() -> str:
    """Return system prompt based on VIDEO_PROMPT_STYLE config."""
    try:
        from config import VIDEO_PROMPT_STYLE
        style = VIDEO_PROMPT_STYLE
    except (ImportError, AttributeError):
        style = "v2"
    return _SYSTEM_PROMPT_V2 if style == "v2" else _SYSTEM_PROMPT_V1


# Alias for backward compatibility
_SYSTEM_PROMPT = _SYSTEM_PROMPT_V2


# -- Builder class ---------------------------------------------------------


class VideoPromptBuilder:
    """Generates LLM-powered motion prompts for Kie.ai Sora 2 video generation.

    Uses Gemini (via src.llm_client) to create unique motion descriptions
    per video, incorporating theme metadata and per-theme improvement notes.

    Usage::

        builder = VideoPromptBuilder()
        prompt = builder.build_motion_prompt(
            theme_key="cafe",
            phrase_context="Cafe e o unico relacionamento estavel que eu mantenho",
            video_prompt_notes="Slow camera push-in works well, avoid fast zooms",
        )
    """

    def build_motion_prompt(
        self,
        theme_key: str,
        phrase_context: str = "",
        pose: str = "",
        scene: str = "",
        video_prompt_notes: str = "",
    ) -> str:
        """Generate a unique LLM-powered motion prompt for a video.

        Per D-02: Each video gets a tailored motion prompt from Gemini.
        Per D-03: video_prompt_notes accumulate learnings for iterative improvement.

        Args:
            theme_key: Theme key from SCENE_TEMPLATES (e.g., "cafe", "sabedoria").
            phrase_context: The meme phrase text -- motion relates to content.
            pose: Character pose description (if available from image metadata).
            scene: Scene description (if available from image metadata).
            video_prompt_notes: Accumulated improvement notes for this theme (D-03).

        Returns:
            Motion prompt string for Kie.ai Sora 2 API.
        """
        templates = _get_templates()
        base_motion = templates.get(theme_key, templates["generico"])

        try:
            from src.llm_client import generate

            # Build user message with all available context
            parts = [f"Base motion idea: {base_motion}"]
            parts.append(f"Theme: {theme_key}")

            if phrase_context:
                parts.append(f"Phrase context: {phrase_context}")
            if pose:
                parts.append(f"Character pose: {pose}")
            if scene:
                parts.append(f"Scene description: {scene}")
            if video_prompt_notes:
                parts.append(f"Improvement notes: {video_prompt_notes}")

            user_message = "\n".join(parts)

            # Call LLM with tier="lite" for cost efficiency (~$0.001/prompt)
            raw = generate(
                system_prompt=_get_system_prompt(),
                user_message=user_message,
                max_tokens=200,
                tier="lite",
            )

            # Clean up LLM response
            prompt = self._clean_llm_response(raw)

            # Validate length -- fall back if LLM returned garbage
            if not prompt or len(prompt) < 10:
                logger.warning(
                    "LLM returned too-short prompt (%d chars), using fallback",
                    len(prompt) if prompt else 0,
                )
                return self.get_fallback_prompt(theme_key)

            # Per D-07: Cap at 500 chars (research: 300-500 sweet spot for i2v)
            if len(prompt) > 500:
                prompt = prompt[:500].rsplit(" ", 1)[0]

            logger.info(
                "Motion prompt generated for theme=%s: %s",
                theme_key, prompt[:80],
            )
            return prompt

        except Exception as e:
            logger.warning(
                "LLM failed for motion prompt (theme=%s): %s -- using fallback",
                theme_key, e,
            )
            return self.get_fallback_prompt(theme_key)

    def enhance_user_prompt(self, user_input: str, theme_key: str = "") -> str:
        """Enhance a user-provided animation description into an optimal Sora 2 prompt.

        Takes the user's brief description and applies prompt engineering to make
        it technically precise for Sora 2, preserving original scene and adding
        subtle motion details.

        Args:
            user_input: User's animation description (e.g., "mago mexendo no cajado").
            theme_key: Optional theme key for context.

        Returns:
            Enhanced Sora 2 prompt.
        """
        try:
            from src.llm_client import generate

            base_motion = MOTION_TEMPLATES.get(theme_key, MOTION_TEMPLATES.get("generico", ""))
            user_message = (
                f"User's animation idea: {user_input}\n"
                f"Theme context: {theme_key or 'general'}\n"
                f"Reference motion style: {base_motion}"
            )

            raw = generate(
                system_prompt=_ENHANCE_PROMPT,
                user_message=user_message,
                max_tokens=200,
                tier="lite",
            )
            prompt = self._clean_llm_response(raw)

            if not prompt or len(prompt) < 10:
                return self._build_safe_prompt(user_input)

            if len(prompt) > 500:
                prompt = prompt[:500].rsplit(" ", 1)[0]

            logger.info("Enhanced user prompt: %s → %s", user_input[:40], prompt[:80])
            return prompt

        except Exception as e:
            logger.warning("LLM enhance failed: %s — using safe wrapper", e)
            return self._build_safe_prompt(user_input)

    @staticmethod
    def _build_safe_prompt(user_input: str) -> str:
        """Wrap user input with safe Sora 2 directives when LLM is unavailable."""
        return (
            f"{user_input}. "
            "Static camera, very slow push-in. "
            "Preserve original scene, lighting, and background. "
            "No speech, no text. Subtle animation only. "
            "Maintain cartoon cel-shading art style."
        )

    def get_fallback_prompt(self, theme_key: str) -> str:
        """Return a static fallback motion prompt when LLM is unavailable.

        Combines the base template entry with a generic camera instruction.

        Args:
            theme_key: Theme key for motion template lookup.

        Returns:
            Static motion prompt with camera instruction.
        """
        templates = _get_templates()
        base_motion = templates.get(theme_key, templates["generico"])
        prompt = (
            f"{base_motion}. "
            "Camera slowly pushes in. "
            "Maintain cartoon cel-shading art style."
        )
        logger.debug("Fallback motion prompt for theme=%s", theme_key)
        return prompt

    # -- Internal helpers --------------------------------------------------

    @staticmethod
    def _clean_llm_response(raw: str) -> str:
        """Strip quotes, whitespace, and common LLM prefix artifacts."""
        text = raw.strip()
        # Remove surrounding quotes
        if (text.startswith('"') and text.endswith('"')) or \
           (text.startswith("'") and text.endswith("'")):
            text = text[1:-1].strip()
        # Remove common LLM prefixes
        lower = text.lower()
        for prefix in ("here is", "here's", "motion prompt:", "prompt:"):
            if lower.startswith(prefix):
                text = text[len(prefix):].strip()
                # Remove leading colon/dash if present
                if text and text[0] in (":", "-", " "):
                    text = text[1:].strip()
                break
        return text
