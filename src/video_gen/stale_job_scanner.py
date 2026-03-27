"""Stale video job scanner -- detects and marks stuck jobs as failed.

Jobs with video_status="generating" for longer than STALE_THRESHOLD_MINUTES
are automatically marked as failed. Runs as an asyncio background task
started during FastAPI lifespan (Phase 18).

Before marking as failed, checks Kie.ai task status:
- Task still active -> skip (not actually stale)
- Task succeeded -> process result
- Task failed -> mark with Kie.ai error message
- Task not found / error -> mark as timed out
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

logger = logging.getLogger("clip-flow.stale_scanner")

# ── Configuration ────────────────────────────────────────────────────────

STALE_THRESHOLD_MINUTES = 15
SCAN_INTERVAL_SECONDS = 300  # 5 minutes


# ── Scanner logic ────────────────────────────────────────────────────────


async def scan_stale_jobs() -> None:
    """Scan for video jobs stuck in 'generating' state and mark them as failed.

    Uses get_session_factory() for an independent DB session (same pattern
    as _generate_video_task in video routes).
    """
    from src.database.session import get_session_factory
    from src.database.models import ContentPackage

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=STALE_THRESHOLD_MINUTES)

    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(
            select(ContentPackage).where(
                ContentPackage.video_status == "generating",
                ContentPackage.created_at < cutoff,
            )
        )
        stale_packages = result.scalars().all()

        if not stale_packages:
            return

        failed_count = 0
        total = len(stale_packages)

        for pkg in stale_packages:
            if pkg.video_task_id:
                # Check actual Kie.ai status before marking as failed
                try:
                    from src.video_gen.kie_client import KieSora2Client, KieAPIError

                    client = KieSora2Client()
                    task_data = await client.get_task_status(pkg.video_task_id)
                    state = task_data.get("state", "")

                    if state == "success":
                        # Task actually succeeded -- update status
                        pkg.video_status = "success"
                        pkg.video_metadata = {
                            **(pkg.video_metadata or {}),
                            "recovered_by": "stale_scanner",
                        }
                        logger.info(
                            "Package %d recovered: Kie.ai task %s succeeded",
                            pkg.id, pkg.video_task_id,
                        )
                        continue

                    if state == "fail":
                        fail_msg = task_data.get("failMsg", "Unknown Kie.ai error")
                        pkg.video_status = "failed"
                        pkg.video_metadata = {
                            **(pkg.video_metadata or {}),
                            "error": f"Kie.ai: {fail_msg}",
                        }
                        failed_count += 1
                        logger.warning(
                            "Package %d: Kie.ai task %s failed: %s",
                            pkg.id, pkg.video_task_id, fail_msg,
                        )
                        continue

                    # Still active (waiting, queuing, generating) -- skip
                    active_states = {"waiting", "queuing", "generating"}
                    if state in active_states:
                        logger.debug(
                            "Package %d: task %s still active (state=%s), skipping",
                            pkg.id, pkg.video_task_id, state,
                        )
                        continue

                    # Unknown state -- mark as failed
                    pkg.video_status = "failed"
                    pkg.video_metadata = {
                        **(pkg.video_metadata or {}),
                        "error": f"Unknown Kie.ai state: {state}",
                    }
                    failed_count += 1

                except KieAPIError as e:
                    if e.code == 404:
                        pkg.video_status = "failed"
                        pkg.video_metadata = {
                            **(pkg.video_metadata or {}),
                            "error": "Kie.ai task not found",
                        }
                    else:
                        pkg.video_status = "failed"
                        pkg.video_metadata = {
                            **(pkg.video_metadata or {}),
                            "error": "Timeout: geracao excedeu o tempo limite",
                        }
                    failed_count += 1

                except Exception:
                    # Any other error -- mark as timed out
                    pkg.video_status = "failed"
                    pkg.video_metadata = {
                        **(pkg.video_metadata or {}),
                        "error": "Timeout: geracao excedeu o tempo limite",
                    }
                    failed_count += 1
            else:
                # No task_id -- job never submitted to Kie.ai
                pkg.video_status = "failed"
                pkg.video_metadata = {
                    **(pkg.video_metadata or {}),
                    "error": "Timeout: geracao excedeu o tempo limite",
                }
                failed_count += 1

        await session.commit()
        logger.info(
            "Stale scan: checked %d, marked %d as failed", total, failed_count,
        )


# ── Background task loop ─────────────────────────────────────────────────

_scanner_task: asyncio.Task | None = None


async def _scanner_loop() -> None:
    """Infinite loop that runs scan_stale_jobs at SCAN_INTERVAL_SECONDS."""
    while True:
        try:
            await scan_stale_jobs()
        except Exception as e:
            logger.error("Stale job scanner error: %s", e)
        await asyncio.sleep(SCAN_INTERVAL_SECONDS)


def start_stale_job_scanner() -> None:
    """Start the stale job scanner as an asyncio background task."""
    global _scanner_task
    loop = asyncio.get_event_loop()
    _scanner_task = loop.create_task(_scanner_loop())
    logger.info(
        "Stale job scanner started (threshold=%dm, interval=%ds)",
        STALE_THRESHOLD_MINUTES,
        SCAN_INTERVAL_SECONDS,
    )


def stop_stale_job_scanner() -> None:
    """Stop the stale job scanner background task."""
    global _scanner_task
    if _scanner_task:
        _scanner_task.cancel()
        _scanner_task = None
        logger.info("Stale job scanner stopped")
