"""Image uploader — provides publicly accessible URLs for Kie.ai API.

Strategy: GCS (if configured) → temporary public upload (fallback).
The fallback uses litterbox.catbox.moe (free, no API key, 1-hour expiry).
"""

import logging
from pathlib import Path

from config import GCS_BUCKET_NAME, GCS_SIGNED_URL_EXPIRY

logger = logging.getLogger("clip-flow.gcs_uploader")


class GCSUploader:
    """Upload local images and return public URLs for Kie.ai consumption.

    Tries GCS first. Falls back to free temporary hosting if GCS is not configured.
    """

    def __init__(self, bucket_name: str | None = None):
        self._bucket_name = bucket_name or GCS_BUCKET_NAME
        self._client = None
        self._bucket = None
        self._gcs_available = None

    def _try_init_gcs(self) -> bool:
        """Try to initialize GCS client. Returns True if available."""
        if self._gcs_available is not None:
            return self._gcs_available
        if not self._bucket_name:
            self._gcs_available = False
            return False
        try:
            from google.cloud import storage
            self._client = storage.Client()
            self._bucket = self._client.bucket(self._bucket_name)
            self._gcs_available = True
            logger.info(f"GCS client initialized, bucket={self._bucket_name}")
            return True
        except Exception as e:
            logger.warning(f"GCS not available ({e}), will use temporary upload fallback")
            self._gcs_available = False
            return False

    def upload_image(self, local_path: str, remote_name: str | None = None) -> str:
        """Upload image and return a public URL.

        Tries GCS first. Falls back to temporary public hosting.
        """
        path = Path(local_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {local_path}")

        if self._try_init_gcs():
            return self._upload_gcs(path, remote_name)
        return self._upload_temp(path)

    def _upload_gcs(self, path: Path, remote_name: str | None = None) -> str:
        """Upload via GCS with signed URL."""
        from datetime import timedelta

        blob_name = remote_name or f"video-inputs/{path.name}"
        blob = self._bucket.blob(blob_name)
        content_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        blob.upload_from_filename(str(path), content_type=content_type)

        signed_url = blob.generate_signed_url(
            expiration=timedelta(seconds=GCS_SIGNED_URL_EXPIRY),
            method="GET",
        )
        logger.info(f"GCS upload: {path.name} → gs://{self._bucket_name}/{blob_name}")
        return signed_url

    def _upload_temp(self, path: Path) -> str:
        """Upload via litterbox.catbox.moe (free, 1h expiry, no API key)."""
        import httpx

        with open(path, "rb") as f:
            resp = httpx.post(
                "https://litterbox.catbox.moe/resources/internals/api.php",
                data={"reqtype": "fileupload", "time": "1h"},
                files={"fileToUpload": (path.name, f, "image/png")},
                timeout=60,
            )
        resp.raise_for_status()
        url = resp.text.strip()
        if not url.startswith("http"):
            raise RuntimeError(f"Temp upload failed: {resp.text}")
        logger.info(f"Temp upload: {path.name} → {url} (expires 1h)")
        return url

    def delete_blob(self, blob_name: str) -> bool:
        """Delete a GCS blob (no-op for temp uploads)."""
        if not self._gcs_available:
            return False
        try:
            blob = self._bucket.blob(blob_name)
            if blob.exists():
                blob.delete()
                logger.info(f"Deleted gs://{self._bucket_name}/{blob_name}")
                return True
        except Exception:
            pass
        return False
