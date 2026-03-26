"""VideoPromptBuilder — generates LLM-powered motion prompts for Kie.ai Sora 2.

Per D-02: Each video gets a unique motion prompt from Gemini, tailored to theme/pose/scene.
Per D-03: video_prompt_notes per theme accumulate learnings (e.g., "avoid fast camera").
The LLM reads these notes when generating prompts, creating an iterative improvement loop.

Per D-01: Videos use the raw background image (no text/watermark). Text is added later by FFmpeg in Phase 999.2.
"""

import logging

logger = logging.getLogger("clip-flow.video_prompt_builder")

# ── Motion templates per theme ──────────────────────────────────────────
# Base motion descriptions used as LLM context, NOT as final prompts.
# Keys match SCENE_TEMPLATES in src/image_gen/prompt_builder.py.

MOTION_TEMPLATES: dict[str, str] = {
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


# ── System prompt for LLM ──────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "You generate SHORT motion/animation prompts for Sora 2 image-to-video AI. "
    "You receive an image of a wizard character meme and must describe ONLY the animation/motion.\n\n"
    "CRITICAL RULES:\n"
    "- Output ONLY the motion prompt (1-3 sentences, max 200 chars)\n"
    "- ANIMATION ONLY: subtle character movement, ambient effects, camera motion\n"
    "- PRESERVE the original scene: same background, same lighting, same colors, same environment\n"
    "- NO speech, NO dialogue, NO mouth movement, NO text, NO words\n"
    "- NO scene changes, NO transitions, NO new elements, NO lighting changes\n"
    "- Camera: prefer static or very slow push-in. NO fast zooms, NO pans, NO rotations\n"
    "- Movement must be SUBTLE: gentle sway, particle drift, hair/cloth flow, breathing\n"
    "- Keep the cartoon cel-shading art style of the original image\n"
    "- Portrait 4:5 aspect ratio\n"
    "- NEVER describe the character appearance (it's already in the image)\n"
    "- Think of it as a LIVING PHOTO — the scene comes alive with minimal, elegant motion"
)

_ENHANCE_PROMPT = (
    "You are a prompt engineer for Sora 2 image-to-video AI. "
    "The user provided a brief animation description. Enhance it into an optimal Sora 2 prompt.\n\n"
    "RULES:\n"
    "- Keep the user's INTENT but make it technically precise for Sora 2\n"
    "- Output 1-3 sentences, max 200 chars\n"
    "- Add: camera instruction (static or slow push-in), ambient particle effects\n"
    "- PRESERVE: original background, lighting, colors, environment — NO changes\n"
    "- NO speech, NO dialogue, NO mouth movement, NO text\n"
    "- Movement must be SUBTLE and elegant\n"
    "- Keep cartoon cel-shading art style\n"
    "- Output ONLY the enhanced prompt, nothing else"
)


# ── Builder class ───────────────────────────────────────────────────────


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
            phrase_context: The meme phrase text — motion relates to content.
            pose: Character pose description (if available from image metadata).
            scene: Scene description (if available from image metadata).
            video_prompt_notes: Accumulated improvement notes for this theme (D-03).

        Returns:
            Motion prompt string for Kie.ai Sora 2 API.
        """
        base_motion = MOTION_TEMPLATES.get(
            theme_key, MOTION_TEMPLATES["generico"]
        )

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
                system_prompt=_SYSTEM_PROMPT,
                user_message=user_message,
                max_tokens=200,
                tier="lite",
            )

            # Clean up LLM response
            prompt = self._clean_llm_response(raw)

            # Validate length — fall back if LLM returned garbage
            if not prompt or len(prompt) < 10:
                logger.warning(
                    "LLM returned too-short prompt (%d chars), using fallback",
                    len(prompt) if prompt else 0,
                )
                return self.get_fallback_prompt(theme_key)

            # Cap at 500 chars (Sora 2 allows 10k but short prompts work better)
            if len(prompt) > 500:
                prompt = prompt[:500].rsplit(" ", 1)[0]

            logger.info(
                "Motion prompt generated for theme=%s: %s",
                theme_key, prompt[:80],
            )
            return prompt

        except Exception as e:
            logger.warning(
                "LLM failed for motion prompt (theme=%s): %s — using fallback",
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

        Combines the base MOTION_TEMPLATES entry with a generic camera instruction.

        Args:
            theme_key: Theme key for motion template lookup.

        Returns:
            Static motion prompt with camera instruction.
        """
        base_motion = MOTION_TEMPLATES.get(
            theme_key, MOTION_TEMPLATES["generico"]
        )
        prompt = (
            f"{base_motion}. "
            "Camera slowly pushes in. "
            "Maintain cartoon cel-shading art style."
        )
        logger.debug("Fallback motion prompt for theme=%s", theme_key)
        return prompt

    # ── Internal helpers ────────────────────────────────────────────────

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
