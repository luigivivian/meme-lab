# Video Ads with AI — Kie.ai Research Guide

Reference document for product video generation feature brainstorming.
Saved from user-compiled research (March 2026).

## Key Models (via Kie.ai API)

| Model | Best For | Max Duration | Type |
|-------|----------|-------------|------|
| Wan 2.6 I2V | Product image-to-video | 15s | I2V |
| Kling 2.5 Turbo | Physics, dynamic motion | 10s | T2V/I2V |
| Veo 3 Quality | Premium commercials | ~8s | T2V/I2V |
| Seedance 1.5 Pro | Demo + narration + music | Variable | T2V/I2V |
| Sora 2 Pro HD | Storytelling | 15s | T2V/I2V |

## Prompt Structure

```
[SHOT TYPE] + [PRODUCT/ACTION] + [CAMERA MOVEMENT]
+ [LIGHTING] + [ENVIRONMENT] + [AESTHETIC] + [DURATION]
```

## Integration

- API: https://api.kie.ai/v1
- Auth: Bearer token (KIE_API_KEY)
- Existing integration: KieSora2Client in src/video_gen/kie_client.py

## Cost Reference

- Kie.ai: pay-as-you-go credits, ~70% cheaper than competitors
- Hailuo 2.3 Standard: already integrated (R$0.86/6s clip)
