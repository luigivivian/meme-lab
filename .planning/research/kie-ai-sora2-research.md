# Kie.ai Sora 2 API Research — Image-to-Video Integration

**Researched:** 2026-03-26
**Overall confidence:** MEDIUM-HIGH
**Purpose:** Integrate image-to-video generation into the Mago Mestre meme pipeline

## Executive Summary

Kie.ai is a third-party API aggregator that provides access to OpenAI's Sora 2 video generation model at 60-85% lower cost than official OpenAI pricing. It exposes a REST-only API (no Python SDK) with an async job model: you submit a task, get a `taskId`, then poll or receive a webhook callback when generation completes.

For the Mago Mestre pipeline, the flow would be: generate a meme image with Gemini -> upload image to a public URL -> call Kie.ai Sora 2 image-to-video -> poll for result -> download MP4 video. The main integration challenge is that the input image must be at a **publicly accessible URL** (not a local file path), so the pipeline needs an upload step (S3, GCS, or similar).

---

## 1. Authentication

**Method:** Bearer token in Authorization header.

```
Authorization: Bearer <YOUR_API_KEY>
Content-Type: application/json
```

**Key management:** https://kie.ai/api-key

**Security features:**
- Rate limiting per key (hourly, daily, total caps)
- IP whitelist support for server-only access
- Missing/invalid token returns `{"code": 401, "msg": "You do not have access permissions"}`

**Environment variable convention:** `KIE_API_KEY`

---

## 2. Image-to-Video API (Sora 2)

### Create Task

**Endpoint:** `POST https://api.kie.ai/api/v1/jobs/createTask`

**Request body:**

```json
{
  "model": "sora-2-image-to-video",
  "callBackUrl": "https://your-domain.com/api/callback",
  "progressCallBackUrl": "https://your-domain.com/api/progress",
  "input": {
    "prompt": "A wizard slowly raises his staff as magical golden particles swirl around him, camera slowly zooms in",
    "image_urls": ["https://publicly-accessible-url.com/mago-mestre-image.jpg"],
    "aspect_ratio": "portrait",
    "n_frames": "10",
    "remove_watermark": true,
    "upload_method": "s3",
    "character_id_list": []
  }
}
```

### Parameters Reference

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `model` | string | YES | — | Must be `"sora-2-image-to-video"` |
| `input.prompt` | string | YES | — | Text description of desired motion/animation (max 10,000 chars) |
| `input.image_urls` | string[] | YES | — | Array with 1 publicly accessible image URL (JPEG/PNG/WebP, max 10MB) |
| `input.aspect_ratio` | string | NO | `"landscape"` | `"portrait"` or `"landscape"` |
| `input.n_frames` | string | NO | `"10"` | `"10"` (10 seconds) or `"15"` (15 seconds) |
| `input.remove_watermark` | boolean | NO | false | Remove watermark from output |
| `input.upload_method` | string | NO | `"s3"` | `"s3"` or `"oss"` — where generated video is stored |
| `input.character_id_list` | string[] | NO | [] | Max 5 character IDs for character consistency |
| `callBackUrl` | string | NO | — | Webhook URL for completion notification |
| `progressCallBackUrl` | string | NO | — | Webhook URL for progress updates |

### Create Task Response

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "taskId": "task_sora-2-image-to-video_1765184045509"
  }
}
```

**Important:** HTTP 200 only means the task was **created**, NOT completed. The video generation is asynchronous.

---

## 3. Getting Results — Poll or Webhook

### Option A: Polling (recommended for pipeline integration)

**Endpoint:** `GET https://api.kie.ai/api/v1/jobs/recordInfo?taskId={taskId}`

**Headers:** `Authorization: Bearer <YOUR_API_KEY>`

**Response:**

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "taskId": "task_sora-2-image-to-video_1765184045509",
    "model": "sora-2-image-to-video",
    "state": "success",
    "param": "{\"prompt\":\"...\",\"image_urls\":[\"...\"],\"aspect_ratio\":\"portrait\"}",
    "resultJson": "{\"resultUrls\":[\"https://file.example.com/k/xxxxx.mp4\"]}",
    "failCode": "",
    "failMsg": "",
    "costTime": 45000,
    "progress": 100,
    "completeTime": 1698765432000,
    "createTime": 1698765400000,
    "updateTime": 1698765432000
  }
}
```

### Task States

| State | Meaning | Action |
|-------|---------|--------|
| `waiting` | Queued, awaiting processing | Keep polling |
| `queuing` | In the processing queue | Keep polling |
| `generating` | Currently processing | Keep polling |
| `success` | Completed successfully | Extract video URL from `resultJson` |
| `fail` | Task failed | Check `failCode` and `failMsg` |

### Extracting the Video URL

The `resultJson` field is a **JSON string** (not an object) that must be parsed:

```python
import json

result_data = response_json["data"]
if result_data["state"] == "success":
    result = json.loads(result_data["resultJson"])
    video_urls = result["resultUrls"]  # List of video URLs
    video_url = video_urls[0]  # First (usually only) video
```

### Polling Best Practices (from official docs)

- Start with 2-3 second intervals, increase gradually (exponential backoff)
- Stop polling after 10-15 minutes (timeout)
- **Download results immediately** — generated content URLs expire after **24 hours**
- Media files retained on Kie.ai servers for **14 days**
- Prefer callbacks in production to avoid polling overhead

### Option B: Webhook Callback

The webhook receives a POST with JSON body when the task completes. Based on the Runway callback format (Market models likely follow a similar pattern using the `recordInfo` structure):

```json
{
  "code": 200,
  "msg": "success",
  "data": {
    "task_id": "task_sora-2-image-to-video_xxx",
    "video_url": "https://file.example.com/k/xxxxx.mp4",
    "image_url": "https://file.example.com/k/thumb.jpg"
  }
}
```

**Note:** The exact callback payload for Market models (Sora 2) may differ slightly from the Runway-specific callback format. The safest approach is to use polling via `recordInfo` endpoint, which is fully documented.

---

## 4. Error Handling

| HTTP Code | Meaning | Action |
|-----------|---------|--------|
| 200 | Success (task created or info retrieved) | Process normally |
| 401 | Unauthorized — invalid/missing API key | Check KIE_API_KEY |
| 402 | Insufficient credits | Top up account |
| 404 | Task not found | Verify taskId |
| 422 | Validation error (bad params) | Check request body |
| 429 | Rate limited | Back off, retry after delay |
| 455 | Service unavailable | Retry later |
| 500 | Server error | Retry with backoff |
| 501 | Generation failed | Check failMsg, may need different prompt |
| 505 | Feature disabled | Contact support |

---

## 5. Sora 2 Model Specifics

### Available Tiers

| Model ID | Resolution | Use Case |
|----------|-----------|----------|
| `sora-2-image-to-video` | Standard (480-720p) | Fast, cheap, good for social media |
| `sora-2-pro-image-to-video` | 720p | Higher quality details |
| `sora-2-pro-1080p-image-to-video` | 1080p | Premium/HD content |
| `sora-2-characters` | Varies | Character consistency across videos |

### Capabilities

- **Input:** Single reference image + text prompt describing desired motion
- **Output:** MP4 video (10 or 15 seconds)
- **Audio:** Native audio generation with dialogue, ambience, and sound effects
- **Aspect ratios:** Portrait (4:5, 9:16) and Landscape (16:9, etc.)
- **Motion control:** Improved physics consistency, realistic motion
- **Prompt max length:** 10,000 characters

### Limitations

- **No 4K support** (max 1080p with Pro tier)
- **Max 1 input image** per request
- **Image must be publicly accessible URL** (no base64, no local files)
- **Max image size:** 10MB
- **Supported formats:** JPEG, PNG, WebP
- **Generation time:** Typically 30-120 seconds (varies by load)
- **URL expiry:** Generated video URLs expire in 24 hours; files deleted after 14 days

---

## 6. Pricing

### Cost Per Video

| Tier | 10 seconds | 15 seconds | Per Second |
|------|-----------|-----------|------------|
| Sora 2 (standard) | ~$0.15 | ~$0.225 | $0.015/s |
| Sora 2 Pro (720p) | ~$0.45 | ~$0.675 | $0.045/s |
| Sora 2 Pro (1080p) | ~$1.00-$1.30 | ~$1.50-$1.95 | $0.10-$0.13/s |

### Credit System

- **1 credit = $0.005 USD**
- Credits never expire
- API credits and user credits are separate (not interchangeable)
- Automatic top-up threshold available

### Cost Comparison

| Provider | Sora 2 (per second) | Savings vs Official |
|----------|---------------------|---------------------|
| **Kie.ai** | $0.015/s | — |
| OpenAI Official | $0.10/s | Kie.ai is 85% cheaper |
| Fal.ai | $0.10/s | Kie.ai is 85% cheaper |

### Budget Estimate for Mago Mestre

Assuming standard tier, 10-second videos, ~10 videos/day:
- **Daily cost:** ~$1.50
- **Monthly cost:** ~$45
- With watermark removal included in standard tier

---

## 7. Rate Limits

- **20 requests per 10 seconds** (~100+ concurrent tasks)
- Exceeding limit returns HTTP 429 (requests are NOT queued)
- Contact support for higher limits
- Sufficient for the Mago Mestre pipeline (single-digit concurrent tasks)

---

## 8. SDK Availability

**No official Python SDK.** REST-only API using standard `requests` library.

This is straightforward to integrate. The API surface is small (2 endpoints: create task + poll status).

---

## 9. Complete Python Integration Example

Based on patterns from official docs, adapted for Mago Mestre pipeline:

```python
"""
Kie.ai Sora 2 Image-to-Video Client
Adapted from official Kie.ai documentation patterns.
"""
import json
import time
import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

class KieSora2Client:
    """Client for Kie.ai Sora 2 image-to-video API."""

    BASE_URL = "https://api.kie.ai/api/v1"

    def __init__(self, api_key: str):
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def create_video_from_image(
        self,
        image_url: str,
        prompt: str,
        aspect_ratio: str = "portrait",  # "portrait" for 4:5 memes
        n_frames: str = "10",            # "10" or "15" seconds
        remove_watermark: bool = True,
        callback_url: Optional[str] = None,
    ) -> str:
        """
        Submit an image-to-video generation task.
        Returns the taskId for polling.
        """
        payload = {
            "model": "sora-2-image-to-video",
            "input": {
                "prompt": prompt,
                "image_urls": [image_url],
                "aspect_ratio": aspect_ratio,
                "n_frames": n_frames,
                "remove_watermark": remove_watermark,
                "upload_method": "s3",
            },
        }
        if callback_url:
            payload["callBackUrl"] = callback_url

        response = requests.post(
            f"{self.BASE_URL}/jobs/createTask",
            json=payload,
            headers=self.headers,
            timeout=30,
        )
        result = response.json()

        if not response.ok or result.get("code") != 200:
            raise Exception(
                f"Kie.ai create task failed: {result.get('code')} - {result.get('msg')}"
            )

        task_id = result["data"]["taskId"]
        logger.info(f"Sora 2 task created: {task_id}")
        return task_id

    def get_task_status(self, task_id: str) -> dict:
        """Get current task status and results."""
        response = requests.get(
            f"{self.BASE_URL}/jobs/recordInfo",
            params={"taskId": task_id},
            headers=self.headers,
            timeout=30,
        )
        result = response.json()

        if not response.ok or result.get("code") != 200:
            raise Exception(
                f"Kie.ai status check failed: {result.get('code')} - {result.get('msg')}"
            )

        return result["data"]

    def wait_for_video(
        self,
        task_id: str,
        max_wait: int = 600,       # 10 minutes
        initial_interval: int = 5,  # start polling after 5s
        max_interval: int = 30,     # cap at 30s between polls
    ) -> Optional[str]:
        """
        Poll until video is ready. Returns video URL or None on failure.
        Uses exponential backoff.
        """
        start = time.time()
        interval = initial_interval

        while time.time() - start < max_wait:
            time.sleep(interval)

            data = self.get_task_status(task_id)
            state = data.get("state", "")
            progress = data.get("progress", 0)

            logger.info(f"Task {task_id}: state={state}, progress={progress}%")

            if state == "success":
                result = json.loads(data["resultJson"])
                urls = result.get("resultUrls", [])
                if urls:
                    logger.info(f"Video ready: {urls[0]}")
                    return urls[0]
                raise Exception("Task succeeded but no resultUrls found")

            elif state == "fail":
                fail_msg = data.get("failMsg", "Unknown error")
                logger.error(f"Task failed: {fail_msg}")
                return None

            # Exponential backoff, capped
            interval = min(interval * 1.5, max_interval)

        logger.error(f"Task {task_id} timed out after {max_wait}s")
        return None


# --- Usage in Mago Mestre pipeline ---

def animate_meme_image(image_public_url: str, phrase: str) -> Optional[str]:
    """
    Take a generated meme image URL and create a short animation.
    Returns the video URL or None.
    """
    import os

    client = KieSora2Client(api_key=os.getenv("KIE_API_KEY"))

    # Craft a motion prompt based on the meme context
    prompt = (
        f"The wizard in the image slowly raises his glowing staff, "
        f"magical golden particles float around him, subtle wind moves his robe, "
        f"the background has gentle atmospheric motion. "
        f"Maintain the cartoon cel-shading art style. "
        f"Camera slowly pushes in. Cinematic lighting."
    )

    task_id = client.create_video_from_image(
        image_url=image_public_url,
        prompt=prompt,
        aspect_ratio="portrait",  # 4:5 for Instagram
        n_frames="10",            # 10 seconds
        remove_watermark=True,
    )

    video_url = client.wait_for_video(task_id)

    if video_url:
        # Download immediately — URL expires in 24 hours
        response = requests.get(video_url, timeout=120)
        output_path = f"generated_videos/{task_id}.mp4"
        with open(output_path, "wb") as f:
            f.write(response.content)
        return output_path

    return None
```

---

## 10. Integration Considerations for Mago Mestre Pipeline

### Critical: Image Must Be Publicly Accessible

The Kie.ai API does NOT accept:
- Local file paths
- Base64-encoded images
- Private/authenticated URLs

**Solutions (pick one):**

1. **Google Cloud Storage (GCS)** — already in ecosystem (Google API key exists). Upload image, get signed URL with 1-hour expiry, pass to Kie.ai.
2. **S3 presigned URL** — if AWS is available.
3. **Simple HTTP server** — expose local images via ngrok or similar (dev only).
4. **Cloudflare R2** — free egress, S3-compatible API.

**Recommendation:** Use GCS since the project already has Google credentials. Upload the generated Gemini image to a GCS bucket, get a public URL, pass to Kie.ai.

### Async Integration with AsyncPipelineOrchestrator

The existing pipeline uses `asyncio`. Wrap the blocking `requests` calls with `asyncio.to_thread()` (consistent with the project's "wrap not rewrite" principle):

```python
import asyncio

async def create_video_async(client, image_url, prompt):
    task_id = await asyncio.to_thread(
        client.create_video_from_image,
        image_url=image_url,
        prompt=prompt,
        aspect_ratio="portrait",
        n_frames="10",
    )
    video_url = await asyncio.to_thread(
        client.wait_for_video, task_id
    )
    return video_url
```

Or better: use `aiohttp` for true async HTTP if video generation becomes a bottleneck.

### Pipeline Position

```
Phrase Generation (Gemini)
    -> Image Generation (Gemini Image)
        -> [NEW] Upload image to GCS (public URL)
        -> [NEW] Video Generation (Kie.ai Sora 2)
        -> [NEW] Download video + compose with text overlay
    -> Image Composition (Pillow text overlay)
    -> Publishing
```

The video generation step is optional and should be a configurable feature flag since:
- It adds $0.15+ per meme
- It adds 30-120 seconds of generation time
- Not every meme benefits from animation

---

## 11. Open Questions / Gaps

| Question | Status | Impact |
|----------|--------|--------|
| Exact callback payload format for Market/Sora 2 models | Not fully documented | LOW — polling works fine |
| Output video codec/format (assumed MP4) | Not explicitly stated | LOW — likely MP4 based on URL patterns |
| Character consistency (`character_id_list`) workflow | Unexplored | MEDIUM — could ensure Mago Mestre consistency across videos |
| Audio in generated videos | Confirmed available | Need to decide: keep audio or strip for Instagram memes? |
| Portrait aspect ratio exact dimensions | Not specified (just "portrait") | LOW — likely 1080x1920 or 1080x1350 |
| Video text overlay (adding meme text to video) | Not part of Kie.ai API | Need FFmpeg or MoviePy for post-processing |

---

## 12. Recommendations

1. **Use standard Sora 2 tier** (`sora-2-image-to-video`) at $0.15/10s — sufficient quality for Instagram Reels/Stories.

2. **Use polling, not webhooks** — the pipeline runs as a batch job, not a web server. Polling with exponential backoff is simpler and doesn't require exposing a public endpoint.

3. **10-second videos** — optimal for Instagram Reels engagement and cost. 15 seconds doubles wait time and cost for marginal benefit.

4. **Make video generation optional** — add a `generate_video: bool` flag to the pipeline config. Not every meme needs animation.

5. **Use GCS for image hosting** — leverage existing Google credentials. Upload generated image, get public URL, pass to Kie.ai, delete after video is generated.

6. **Download videos immediately** — URLs expire in 24 hours. Download to local storage as soon as generation completes.

7. **Budget guard** — at $0.15/video and potential for batch runs, add a daily spend limit check before submitting tasks.

---

## Sources

- [Kie.ai Sora 2 Image-to-Video API Docs](https://docs.kie.ai/market/sora2/sora-2-image-to-video)
- [Kie.ai Get Task Details](https://docs.kie.ai/market/common/get-task-detail)
- [Kie.ai Getting Started](https://docs.kie.ai/)
- [Kie.ai Pricing](https://kie.ai/pricing)
- [Kie.ai Sora 2 Overview](https://kie.ai/sora-2)
- [Kie.ai Veo3 Quickstart (Python patterns)](https://docs.kie.ai/veo3-api/quickstart)
- [Kie.ai Runway Callbacks (webhook format)](https://docs.kie.ai/runway-api/generate-ai-video-callbacks)
