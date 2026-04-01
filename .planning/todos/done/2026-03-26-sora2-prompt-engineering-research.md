---
title: Sora 2 Prompt Engineering Research & Application
area: video
priority: high
created: 2026-03-26
status: pending
---

## Problem

Sora 2 videos are generating with static characters and sometimes with voice/speech. The prompts need better engineering to:
1. Animate the CHARACTER as primary subject (not just background)
2. Never generate voice/speech
3. Preserve original scene, lighting, environment
4. Produce high-quality cinematic animation

## Solution

### Research Phase
1. Study https://github.com/ZeroLu/awesome-sora2 — complete resource collection
2. Analyze prompt patterns that produce best character animation results
3. Study Sora 2 limitations and best practices for image-to-video
4. Research other sources for Sora 2 prompt engineering

### Application Phase
1. Rewrite system prompts in `src/video_gen/video_prompt_builder.py` based on research findings
2. Update motion templates with research-backed animation descriptions
3. Add explicit anti-voice/anti-speech directives validated against Sora 2 docs
4. Test with multiple themes and validate quality improvement

## Files
- src/video_gen/video_prompt_builder.py — system prompts + motion templates
- src/video_gen/kie_client.py — API parameters
- src/api/routes/video.py — endpoint handling

## References
- https://github.com/ZeroLu/awesome-sora2
- Kie.ai API docs
- Last failed prompt: "A cartoon wizard, focusing on his torso and arms, raises his staff..." — produced static image with voice
