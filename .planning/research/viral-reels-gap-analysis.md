# Viral Reels Gap Analysis

**Date:** 2026-04-01
**Source:** guia-viral-reels-shorts-tiktok-2026.md vs current pipeline

## Guide Validation

Guide is valid and internally consistent for 2026. Key points confirmed:
- Watch-time/retention as primary algorithm signal
- 5-phase structure (GANCHO/CONTEXTO/CONTEUDO/PAYOFF/LOOP)
- Loop technique for rewatches
- Pattern interrupts every 3-5s
- Hashtag 1-2-2 formula (max 5)
- Faceless content format = exactly what our pipeline produces

## Gap Table

| Concept | Pipeline Status | Gap | Effort |
|---|---|---|---|
| 5-phase script structure | Partial (gancho+CTA exist) | No phase sequencing/timing | Small |
| Hook type variety (5 types) | Not implemented | LLM picks freely | Small |
| Loop verbal (last phrase → first) | Not implemented | No loop instruction | Small |
| Pattern interrupts every 3-5s | Not in schema | No pattern_interrupts field | Medium |
| Visual hook on first frame | Same prompt for all scenes | No special scene 0 instruction | Small |
| TTS pacing (strategic silences) | Not implemented | No pause markers | Medium |
| Subtitle chunks (4-5 words) | 40 chars (~6-8 words) | Too many words per entry | Small |
| Subtitle style (bold sans-serif) | MedievalSharp size 12 | Not bold, too small for mobile | Small |
| Hashtag 1-2-2 formula | Up to 30 allowed | No formula constraint | Small |
| Instagram caption as mini blog | Partial | Not keyword-dense | Small |
| YouTube title SEO | Not enforced | No keyword-first instruction | Small |
| Ken-burns on static path | No motion on images | Slow fade only | Medium |
| Video loop assembly | Not implemented | No loop logic | Large |
| Keywords in spoken audio | Not instructed | Platforms index spoken words | Small |

## Priority Recommendations

1. **5-phase script structure** — prompt edit in script_gen.py (HIGH impact, SMALL effort)
2. **Loop verbal instruction** — add loop field to schema + prompt (HIGH impact, SMALL effort)
3. **Subtitle chunks 40→25 chars** — 1 line change in transcriber.py (HIGH impact, SMALL effort)
4. **Hashtag 1-2-2 formula** — update platform_metadata.py prompt (MEDIUM impact, SMALL effort)
5. **Hook type parameter** — add hook_type to config (MEDIUM impact, SMALL effort)
6. **Ken-burns on static images** — FFmpeg zoompan filter (MEDIUM impact, MEDIUM effort)
7. **First-scene visual hook** — conditional prompt in image_gen.py (MEDIUM impact, SMALL effort)
8. **Keywords in spoken audio** — prompt edit in script_gen.py (MEDIUM impact, SMALL effort)
