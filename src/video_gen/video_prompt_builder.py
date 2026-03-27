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
        "wizard slowly strokes his beard thoughtfully, staff crystal pulses "
        "with faint blue glow, subtle magical particles drift upward"
    ),
    "confusao": (
        "wizard tilts his head back and forth in confusion, magical question "
        "marks float and pop around him, hat wobbles slightly"
    ),
    "segunda_feira": (
        "wizard drowsily sips from coffee goblet, steam rises with golden "
        "sparkles, eyes droop then snap open, slight head nod"
    ),
    "vitoria": (
        "wizard raises staff triumphantly overhead, golden magical particles "
        "erupt from staff tip, robes billow with celebration energy"
    ),
    "tecnologia": (
        "wizard pokes at a glowing crystal device with curiosity, digital "
        "runes flicker around it, hat tilts as he leans in"
    ),
    "cafe": (
        "wizard holds ornate mug with both hands, steam curls upward with "
        "magical sparkles, content smile deepens, gentle breathing motion"
    ),
    "comida": (
        "wizard stirs bubbling cauldron, colorful potion vapors rise and "
        "swirl, floating ingredients orbit lazily, focused expression"
    ),
    "trabalho": (
        "wizard writes on parchment at desk, quill moves with magical trail, "
        "ink transforms into tiny floating runes, focused gaze"
    ),
    "relaxando": (
        "wizard dozes in chair, hat tips over eyes, chest rises and falls "
        "with slow breathing, staff leans and glows faintly"
    ),
    "meditando": (
        "wizard sits in deep meditation, ethereal blue-gold aura pulses "
        "outward in waves, staff hovers gently, serene stillness"
    ),
    "relacionamento": (
        "wizard holds glowing heart-shaped crystal, soft pink and blue "
        "magical aura shifts and flows between hands, gentle knowing expression"
    ),
    "confronto": (
        "wizard plants staff firmly, golden energy bursts from tip, robes "
        "whip in dramatic wind, stern determined gaze forward"
    ),
    "surpresa": (
        "wizard jolts with wide eyes, hat blows back slightly, hands raise "
        "in shock, exclamation-shaped sparkles pop around head"
    ),
    "internet": (
        "wizard gazes into glowing crystal ball with shifting expressions, "
        "blue light reflects on face, occasional surprised reaction"
    ),
    "generico": (
        "wizard stands with staff, subtle magical glow from crystal tip "
        "pulses rhythmically, robes sway gently in ambient breeze"
    ),
    "cotidiano": (
        "wizard leans on staff casually, takes a relaxed sip from ale mug, "
        "faint sparkles drift lazily around him, easy-going posture"
    ),
    "descanso": (
        "wizard peacefully sleeps in wooden chair, hat droops forward, "
        "chest rises and falls slowly, soft blue particles float around"
    ),
}


# -- v2 templates -- Three-layer motion framework (OpenAI Cookbook + awesome-sora2) --
# Per D-02: All 17 themes updated with researched patterns.
# Per D-03: Camera movement + temporal flow + physics focus.
# Per D-04: 4-5 sentences, 300-500 chars per template.
# Per D-08: Technique reference comments for future maintainers.
# Each template: [Camera macro] + [Subject primary + micro] + [Physics/atmosphere]
# Tense: present continuous throughout ("is raising", "are drifting")
# Source: OpenAI Sora 2 Prompting Guide + WaveSpeedAI + awesome-sora2 community

MOTION_TEMPLATES_V2: dict[str, str] = {
    # Camera: slow push-in -- contemplative but with visible gesture (raising hand/staff)
    "sabedoria": (
        "Slow push-in from medium shot. "
        "The wizard raises one hand thoughtfully to his chin, then extends it forward with an open palm as if presenting wisdom. "
        "His staff crystal flares brighter as he lifts the staff slightly, tilting his head with a knowing nod. "
        "Heavy robes swing with the arm gesture, long white beard sways with the head movement, "
        "golden magical particles burst upward from his open palm."
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
    # Camera: slow push-in -- coffee drinking with visible lift/sip/exhale motion
    "cafe": (
        "Slow push-in from medium shot. "
        "The wizard lifts an ornate mug to his lips with both hands, takes a long sip, and pulls it away with a satisfied exhale. "
        "His eyes close as he tilts his head back, then snap open wide with the caffeine kick. "
        "Warm steam billows upward from the mug with golden sparkles, "
        "heavy robe sleeves slide down his forearms as he raises the mug, beard catching the rising steam."
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
    # Camera: slow push-in -- relaxing but with visible stretch/yawn motion
    "relaxando": (
        "Slow push-in from medium shot. "
        "The wizard stretches both arms wide overhead in a long satisfying yawn, fingers splaying outward. "
        "His hat slides forward over his eyes as he sinks deeper into the chair, one hand reaching up to push it back. "
        "Heavy robe fabric is draping and shifting with the stretch, "
        "the staff nearby pulses with a warm golden glow, soft particles drifting upward."
    ),
    # Camera: slow push-in -- meditation needs visible arm/hand motion to avoid static output
    "meditando": (
        "Slow push-in from medium shot. "
        "The wizard raises both hands from his knees to chest height, palms turning upward in a sweeping gesture. "
        "His head tilts back as he lifts his chin toward the sky, eyes closing with concentration. "
        "A blue-gold energy wave bursts outward from his palms, heavy robe sleeves sliding down his forearms, "
        "luminous particles are swirling upward around his body in a spiraling column."
    ),
    # Camera: slow push-in -- emotional theme with visible crystal lift and head turn
    "relacionamento": (
        "Slow push-in from medium shot. "
        "The wizard raises a glowing heart crystal high in one hand, turning it to catch the light, then presses it against his chest. "
        "He closes his eyes and tilts his head to the side with a deep knowing smile. "
        "A pink energy wave pulses outward from the crystal as he clutches it, "
        "heavy robe fabric swings with the arm motion, soft warm light flaring around his hands."
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
    # Camera: slow push-in -- internet browsing with visible lean-in and reaction
    "internet": (
        "Slow push-in from medium shot. "
        "The wizard leans forward sharply toward a glowing crystal ball, gripping it with both hands and pulling it closer. "
        "His eyebrows shoot up in surprise as he jerks his head back, then leans in again with wide curious eyes. "
        "Blue light flares across his face with each reaction, "
        "heavy robes shifting with his animated forward-backward movement, beard swinging with each jolt."
    ),
    # Camera: slow push-in -- generic needs clear staff gesture for reliable animation
    "generico": (
        "Slow push-in from medium shot. "
        "The wizard lifts his staff and swings it forward in a deliberate arc, planting it firmly on the ground. "
        "He turns his head to look directly at the viewer, beard swaying with the sharp head turn. "
        "The crystal tip flares with a bright golden burst on impact, "
        "heavy robes are swinging with the momentum of the staff swing, particles erupting upward."
    ),
    # Camera: static with gentle ambient drift -- casual everyday feel
    "cotidiano": (
        "Static camera with gentle ambient drift. "
        "The wizard is leaning casually on his staff, one ankle crossing the other lazily. "
        "He is raising an ale mug for a relaxed sip, body swaying slightly with the motion. "
        "Faint sparkles are drifting lazily around him, "
        "robe fabric is settling with his casual posture, warm ambient light glowing softly."
    ),
    # Camera: slow push-in -- sleeping but with visible startle/shift motion
    "descanso": (
        "Slow push-in from medium shot. "
        "The wizard is dozing in a wooden chair when his head drops forward suddenly, startling him half-awake. "
        "He jerks his head back up, one hand reaching to catch his hat as it slides off, then slumps back down. "
        "His heavy robes shift and resettle with the sudden movement, "
        "soft blue particles swirl around him as the staff nearby flickers with a sleepy golden glow."
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


# -- System prompts for LLM -----------------------------------------------

# Original v1 system prompts -- preserved for fallback (per D-05)
_SYSTEM_PROMPT_V1 = (
    "You generate SHORT motion/animation prompts for Sora 2 image-to-video AI. "
    "You receive context about a wizard character meme and must describe the MOTION and CAMERA movement.\n\n"
    "RULES:\n"
    "- Output ONLY the motion prompt (2-4 sentences, max 300 chars)\n"
    "- Describe character MOVEMENT (gestures, expressions, body language)\n"
    "- Describe CAMERA movement (slow zoom, pan, static, push in)\n"
    "- Describe AMBIENT motion (particles, wind, magical effects)\n"
    "- Keep the cartoon cel-shading art style\n"
    "- Portrait 4:5 aspect ratio composition\n"
    "- NEVER describe the character's appearance (that's in the image)\n"
    "- NEVER include text or dialogue"
)

# v2 system prompt -- Natural flowing prose for Sora 2 (no labels!)
# Source: OpenAI Sora 2 Prompting Guide + awesome-sora2 community patterns
# KEY LEARNING: Sora 2 reads the prompt as literal text. Labels like "CAMERA:"
# confuse it. Output must be natural flowing sentences. Also "subtle/gentle/slowly"
# everywhere = static video. Use decisive action verbs.
_SYSTEM_PROMPT_V2 = (
    "You generate motion prompts for image-to-video AI models (Hailuo, Kling, Wan). "
    "You receive context about a cartoon wizard character and must describe VISIBLE animation.\n\n"
    "CRITICAL CONTEXT: Image-to-video models are EXTREMELY conservative — they try to keep "
    "the input image unchanged. If you describe subtle motion ('slowly rising', 'gently settling', "
    "'softly pulsing'), the model will produce a STATIC image with zero animation. "
    "You MUST describe EXAGGERATED, DRAMATIC physical motion to get ANY visible movement.\n\n"
    "OUTPUT: Write 3-4 sentences of FLOWING NATURAL PROSE (300-500 chars). "
    "NO labels, NO bullet points, NO numbered lists. Just sentences.\n\n"
    "STRUCTURE YOUR SENTENCES (but do NOT label them):\n"
    "- First sentence: camera movement (slow push-in, static shot, gentle dolly)\n"
    "- Second sentence: the character's MAIN ACTION with STRONG DECISIVE verbs "
    "(raises his staff high, turns his head sharply, lifts the goblet overhead, slams his fist down). "
    "The action must be a LARGE VISIBLE MOVEMENT — arms moving, body turning, objects being lifted\n"
    "- Third sentence: REACTIVE physics from the main action (robes swinging with the turn, "
    "beard whipping with the head movement, liquid sloshing in the goblet)\n"
    "- Fourth sentence: secondary motion and atmosphere (particles bursting, light flaring, "
    "wind picking up)\n\n"
    "CRITICAL RULES:\n"
    "- The character MUST perform a CLEAR PHYSICAL ACTION — moving arms, turning body, "
    "lifting objects, leaning forward, stepping, gesturing broadly. "
    "BANNED weak verbs: 'shifts', 'settles', 'adjusts', 'rests', 'sits'. "
    "REQUIRED strong verbs: raises, swings, turns, lifts, reaches, pulls, pushes, throws, grabs, slams\n"
    "- Even for calm themes (meditation, rest), the character must DO something visible: "
    "raises hands to chest, lifts head upward, extends arms outward, opens eyes wide\n"
    "- Present continuous tense: 'is raising', 'are floating', 'is glowing'\n"
    "- ONE camera movement only — never combine pan + zoom + track\n"
    "- Include physical details: 'heavy fabric', 'wooden staff', 'long white beard'\n"
    "- NO speech, NO text, NO lip movement, NO scene changes\n"
    "- NEVER use labels like 'CAMERA:', 'SUBJECT:', 'PHYSICS:' in your output\n"
    "- NEVER describe character appearance (already in the image)\n"
    "- If a scene description is provided, the animation MUST match that scene "
    "(e.g., if scene is 'wizard collecting fruits', animate fruit picking motion)\n"
    "- Output ONLY the motion prompt sentences, nothing else"
)

# Backward compatibility aliases (point to v2 by default)
_SYSTEM_PROMPT = _SYSTEM_PROMPT_V2


# -- Enhance prompts for LLM -----------------------------------------------

# Original v1 enhance prompt -- preserved for fallback (per D-05)
_ENHANCE_PROMPT_V1 = (
    "You are a prompt engineer for Sora 2 image-to-video AI. "
    "The user described how they want a cartoon wizard character animated. Enhance it.\n\n"
    "RULES:\n"
    "- Keep the user's INTENT but make it technically precise for Sora 2\n"
    "- Output 2-4 sentences, max 300 chars\n"
    "- CHARACTER MUST BE THE FOCUS of animation -- body, arms, head, expressions\n"
    "- Add ambient effects: particles, cloth physics, hair/beard sway\n"
    "- Camera: static or slow push-in\n"
    "- PRESERVE: original background, scene, art style -- NO changes\n"
    "- NO speech, NO lip movement, NO text\n"
    "- Output ONLY the enhanced prompt, nothing else"
)

# v2 enhance prompt -- Natural prose enhancement for Sora 2
_ENHANCE_PROMPT_V2 = (
    "You are a prompt engineer for image-to-video AI (Hailuo, Kling, Wan). "
    "Enhance the user's animation description into an optimal motion prompt.\n\n"
    "CRITICAL: Image-to-video models are EXTREMELY conservative. Subtle descriptions "
    "('gently', 'slowly', 'softly') produce STATIC videos. You must AMPLIFY all motion.\n\n"
    "OUTPUT: 3-4 sentences of FLOWING NATURAL PROSE (300-500 chars). "
    "NO labels, NO bullet points, NO 'CAMERA:', NO 'SUBJECT:'. Just sentences.\n\n"
    "RULES:\n"
    "- Keep the user's INTENT but make the action DRAMATICALLY MORE VISIBLE\n"
    "- Replace ALL weak verbs ('shifts', 'adjusts', 'settles', 'rests') with "
    "STRONG ones ('raises', 'swings', 'turns', 'lifts', 'reaches', 'grabs')\n"
    "- The character MUST perform a clear physical action with arms, body, or head\n"
    "- Add reactive physics: motion CAUSES something (robes swing, beard whips, liquid sloshes)\n"
    "- Present continuous tense: is raising, are floating, is glowing\n"
    "- Add physical details: 'heavy robe fabric billowing', 'wooden staff crystal pulsing'\n"
    "- ONE camera movement (first sentence)\n"
    "- PRESERVE original scene, background, art style — NO changes\n"
    "- NO speech, NO lip movement, NO text\n"
    "- Output ONLY the enhanced prompt sentences, nothing else"
)

# Backward compatibility alias (point to v2 by default)
_ENHANCE_PROMPT = _ENHANCE_PROMPT_V2


# -- Version-aware prompt selection ----------------------------------------


def _get_system_prompt() -> str:
    """Return active system prompt based on VIDEO_PROMPT_STYLE config.

    Per D-06: v2 uses structured sections (CAMERA/SUBJECT/PHYSICS/ATMOSPHERE).
    """
    try:
        from config import VIDEO_PROMPT_STYLE
        style = VIDEO_PROMPT_STYLE
    except (ImportError, AttributeError):
        style = os.getenv("VIDEO_PROMPT_STYLE", "v2")

    if style == "v1":
        return _SYSTEM_PROMPT_V1
    return _SYSTEM_PROMPT_V2


def _get_enhance_prompt() -> str:
    """Return active enhance prompt based on VIDEO_PROMPT_STYLE config."""
    try:
        from config import VIDEO_PROMPT_STYLE
        style = VIDEO_PROMPT_STYLE
    except (ImportError, AttributeError):
        style = os.getenv("VIDEO_PROMPT_STYLE", "v2")

    if style == "v1":
        return _ENHANCE_PROMPT_V1
    return _ENHANCE_PROMPT_V2


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

            # Build user message — scene and phrase are PRIMARY context
            parts = []
            if scene:
                parts.append(f"IMPORTANT — The image shows: {scene}")
                parts.append("The animation MUST depict this specific scene. Do NOT use generic wizard motion.")
            if phrase_context:
                parts.append(f"Meme phrase: {phrase_context}")
            parts.append(f"Theme: {theme_key}")
            parts.append(f"Reference motion style (adapt to match the scene above): {base_motion}")
            if pose:
                parts.append(f"Character pose: {pose}")
            if video_prompt_notes:
                parts.append(f"Improvement notes: {video_prompt_notes}")

            user_message = "\n".join(parts)

            # Call LLM with tier="lite" for cost efficiency (~$0.001/prompt)
            # Per D-07: max_tokens 250 for v2 (4-5 sentences, 300-500 chars)
            raw = generate(
                system_prompt=_get_system_prompt(),
                user_message=user_message,
                max_tokens=250,
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

            templates = _get_templates()
            base_motion = templates.get(theme_key, templates.get("generico", ""))
            user_message = (
                f"User's animation idea: {user_input}\n"
                f"Theme context: {theme_key or 'general'}\n"
                f"Reference motion style: {base_motion}"
            )

            # Per D-07: max_tokens 250 for v2 (4-5 sentences, 300-500 chars)
            raw = generate(
                system_prompt=_get_enhance_prompt(),
                user_message=user_message,
                max_tokens=250,
                tier="lite",
            )
            prompt = self._clean_llm_response(raw)

            if not prompt or len(prompt) < 10:
                return self._build_safe_prompt(user_input)

            # Per D-07: Cap at 500 chars (research: 300-500 sweet spot for i2v)
            if len(prompt) > 500:
                prompt = prompt[:500].rsplit(" ", 1)[0]

            logger.info("Enhanced user prompt: %s -> %s", user_input[:40], prompt[:80])
            return prompt

        except Exception as e:
            logger.warning("LLM enhance failed: %s -- using safe wrapper", e)
            return self._build_safe_prompt(user_input)

    @staticmethod
    def _build_safe_prompt(user_input: str) -> str:
        """Wrap user input with safe Sora 2 directives when LLM is unavailable."""
        return (
            f"Static camera, locked-off shot. {user_input}. "
            "Character is the primary subject of animation. "
            "Robe fabric is swaying gently, ambient particles are drifting. "
            "Maintain cartoon cel-shading art style, portrait 4:5."
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
