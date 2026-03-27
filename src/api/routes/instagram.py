"""Instagram API routes — OAuth flow, connection status, media upload to GCS.

Endpoints:
  GET  /instagram/auth-url     — Facebook OAuth URL for frontend popup (D-07)
  GET  /instagram/callback     — Exchange OAuth code for long-lived token (D-08)
  GET  /instagram/status       — Connection status for authenticated user (D-09)
  POST /instagram/disconnect   — Revoke and remove connection (D-10)
  POST /instagram/upload-media — Upload image to GCS, return signed URL (D-11)
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import db_session, get_current_user
from src.services.instagram_oauth import InstagramOAuthService, InstagramOAuthError

logger = logging.getLogger("clip-flow.api.instagram")

router = APIRouter(prefix="/instagram", tags=["Instagram"])


# ── Pydantic models ──────────────────────────────────────────────────────────

class UploadMediaRequest(BaseModel):
    content_package_id: int


# ── GET /instagram/auth-url ──────────────────────────────────────────────────

@router.get("/auth-url", summary="Get Facebook OAuth URL for Instagram connection")
async def auth_url(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Generate Facebook OAuth URL with CSRF state token (per D-07).

    Frontend opens this URL in a popup. After user grants permissions,
    Facebook redirects back with a code that the frontend sends to /callback.
    """
    service = InstagramOAuthService(session)
    result = service.generate_auth_url()
    return result


# ── GET /instagram/callback ──────────────────────────────────────────────────

@router.get("/callback", summary="Exchange OAuth code for long-lived token")
async def callback(
    code: str = Query(..., description="Authorization code from Facebook OAuth redirect"),
    state: str = Query(default="", description="CSRF state token (frontend validates client-side)"),
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Exchange authorization code for long-lived token and store connection (per D-08).

    Called by the frontend after the OAuth popup redirects back.
    The frontend extracts the code from URL params and calls this endpoint.
    """
    try:
        connection = await InstagramOAuthService(session).exchange_code(
            code=code, user_id=current_user.id,
        )
        return {
            "success": True,
            "ig_username": connection.ig_username,
            "connected_at": str(connection.connected_at),
        }
    except InstagramOAuthError as e:
        raise HTTPException(status_code=400, detail=e.message)


# ── GET /instagram/status ────────────────────────────────────────────────────

@router.get("/status", summary="Get Instagram connection status")
async def status(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Return connection status for the authenticated user (per D-09).

    Returns the status dict or {"connected": False} if no connection exists.
    """
    result = await InstagramOAuthService(session).get_status(user_id=current_user.id)
    if result is None:
        return {"connected": False}
    return result


# ── POST /instagram/disconnect ───────────────────────────────────────────────

@router.post("/disconnect", summary="Disconnect Instagram account")
async def disconnect(
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Revoke token and remove Instagram connection (per D-10).

    Returns {"success": True} or 404 if no connection found.
    """
    disconnected = await InstagramOAuthService(session).disconnect(user_id=current_user.id)
    if not disconnected:
        raise HTTPException(status_code=404, detail="No Instagram connection found")
    return {"success": True}


# ── POST /instagram/upload-media ─────────────────────────────────────────────

@router.post("/upload-media", summary="Upload image to GCS for Instagram publishing")
async def upload_media(
    req: UploadMediaRequest,
    current_user=Depends(get_current_user),
    session: AsyncSession = Depends(db_session),
):
    """Upload content package image to GCS and return signed URL (per D-11, D-01, D-02).

    The signed URL is publicly accessible for 1 hour, which Instagram Graph API
    needs to fetch the image during container creation.
    """
    from src.database.models import ContentPackage, PipelineRun, Character
    from config import GCS_SIGNED_URL_EXPIRY

    # Load content package
    result = await session.execute(
        select(ContentPackage).where(ContentPackage.id == req.content_package_id)
    )
    package = result.scalar_one_or_none()
    if not package:
        raise HTTPException(status_code=404, detail="Content package not found")

    # Verify ownership: content_package -> pipeline_run -> character -> user_id
    # or content_package -> character -> user_id
    owner_id = None
    if package.character_id:
        char_result = await session.execute(
            select(Character.user_id).where(Character.id == package.character_id)
        )
        owner_id = char_result.scalar_one_or_none()

    if owner_id is None and package.pipeline_run_id:
        run_result = await session.execute(
            select(PipelineRun.character_id).where(PipelineRun.id == package.pipeline_run_id)
        )
        run_char_id = run_result.scalar_one_or_none()
        if run_char_id:
            char_result = await session.execute(
                select(Character.user_id).where(Character.id == run_char_id)
            )
            owner_id = char_result.scalar_one_or_none()

    if owner_id is not None and owner_id != current_user.id and not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Forbidden")

    # Check image file exists
    image_path = Path(package.image_path)
    if not image_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Image file not found: {package.image_path}",
        )

    # Upload to GCS via GCSUploader (per D-01: use existing bucket)
    try:
        from src.video_gen.gcs_uploader import GCSUploader

        uploader = GCSUploader(bucket_name="meme-lab-bucket")
        remote_name = f"instagram-media/{package.id}/{image_path.name}"
        signed_url = uploader.upload_image(str(image_path), remote_name=remote_name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Image file not found on disk")
    except Exception as e:
        logger.error("GCS upload failed for content_package_id=%d: %s", package.id, e)
        raise HTTPException(status_code=500, detail=f"GCS upload failed: {e}")

    return {
        "cdn_url": signed_url,
        "content_package_id": package.id,
        "expires_in_seconds": GCS_SIGNED_URL_EXPIRY,
    }
