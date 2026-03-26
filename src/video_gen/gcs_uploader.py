"""GCS Uploader -- uploads images to Google Cloud Storage for public URL access.

Per D-04: Use GCS for image uploads to provide publicly accessible URLs
to the Kie.ai API. Independent of Phase 14 (Cloudflare R2 is for Instagram CDN).

Signed URLs expire after GCS_SIGNED_URL_EXPIRY seconds (default 1 hour).
"""

import logging
from datetime import timedelta
from pathlib import Path

from config import GCS_BUCKET_NAME, GCS_SIGNED_URL_EXPIRY

logger = logging.getLogger("clip-flow.gcs_uploader")


class GCSUploader:
    """Upload local images to GCS and return signed URLs for Kie.ai consumption."""

    def __init__(self, bucket_name: str | None = None):
        self._bucket_name = bucket_name or GCS_BUCKET_NAME
        self._client = None
        self._bucket = None

    def _ensure_client(self):
        """Lazy-init GCS client.

        Uses Application Default Credentials or GOOGLE_APPLICATION_CREDENTIALS env var.
        """
        if self._client is None:
            try:
                from google.cloud import storage

                self._client = storage.Client()
                self._bucket = self._client.bucket(self._bucket_name)
                logger.info(f"GCS client initialized, bucket={self._bucket_name}")
            except Exception as e:
                logger.error(f"Failed to initialize GCS client: {e}")
                raise

    def upload_image(self, local_path: str, remote_name: str | None = None) -> str:
        """Upload a local image file to GCS and return a signed URL.

        Args:
            local_path: Absolute path to the local image file.
            remote_name: Optional custom name in GCS. Defaults to filename.

        Returns:
            Signed URL string accessible for GCS_SIGNED_URL_EXPIRY seconds.

        Raises:
            FileNotFoundError: If local_path does not exist.
            Exception: If GCS upload fails.
        """
        self._ensure_client()

        path = Path(local_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {local_path}")

        blob_name = remote_name or f"video-inputs/{path.name}"
        blob = self._bucket.blob(blob_name)

        content_type = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        blob.upload_from_filename(str(path), content_type=content_type)

        signed_url = blob.generate_signed_url(
            expiration=timedelta(seconds=GCS_SIGNED_URL_EXPIRY),
            method="GET",
        )

        logger.info(
            f"Uploaded {path.name} to gs://{self._bucket_name}/{blob_name} "
            f"(URL expires in {GCS_SIGNED_URL_EXPIRY}s)"
        )
        return signed_url

    def delete_blob(self, blob_name: str) -> bool:
        """Delete a blob from GCS (cleanup after video generation).

        Returns True if deleted, False if not found.
        """
        self._ensure_client()
        blob = self._bucket.blob(blob_name)
        if blob.exists():
            blob.delete()
            logger.info(f"Deleted gs://{self._bucket_name}/{blob_name}")
            return True
        return False
