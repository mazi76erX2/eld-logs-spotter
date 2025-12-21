import io
import logging
from typing import Optional

from django.conf import settings
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


class StorageService:
    """
    Service for handling file storage.
    Automatically uses Cloudinary in production, local storage in development.
    """

    @staticmethod
    def is_cloudinary_enabled() -> bool:
        """Check if Cloudinary storage is enabled."""
        return (
            hasattr(settings, "CLOUDINARY_STORAGE")
            and settings.CLOUDINARY_STORAGE.get("CLOUD_NAME")
            and getattr(settings, "STORAGE_BACKEND", "local") == "cloudinary"
        )

    @classmethod
    def upload_image(
        cls,
        image_bytes: bytes,
        filename: str,
        folder: str = "eld_logs",
        resource_type: str = "image",
    ) -> Optional[str]:
        """
        Upload an image and return the URL.
        """
        if cls.is_cloudinary_enabled():
            return cls._upload_to_cloudinary(
                image_bytes, filename, folder, resource_type
            )
        else:
            return cls._save_locally(image_bytes, filename, folder)

    @classmethod
    def _upload_to_cloudinary(
        cls,
        image_bytes: bytes,
        filename: str,
        folder: str,
        resource_type: str,
    ) -> Optional[str]:
        """Upload to Cloudinary."""
        try:
            import cloudinary.uploader

            # Remove extension for public_id
            public_id = filename.rsplit(".", 1)[0]

            result = cloudinary.uploader.upload(
                io.BytesIO(image_bytes),
                public_id=f"{folder}/{public_id}",
                resource_type=resource_type,
                overwrite=True,
                format="png",
                transformation=[
                    {"quality": "auto:best"},
                    {"fetch_format": "auto"},
                ],
            )

            url = result.get("secure_url")
            logger.info(f"Uploaded to Cloudinary: {url}")
            return url

        except Exception as e:
            logger.error(f"Cloudinary upload failed: {e}", exc_info=True)
            return None

    @classmethod
    def _save_locally(
        cls,
        image_bytes: bytes,
        filename: str,
        folder: str,
    ) -> Optional[str]:
        """Save to local filesystem."""
        try:
            from django.core.files.storage import default_storage

            path = f"{folder}/{filename}"
            saved_path = default_storage.save(path, ContentFile(image_bytes))
            url = default_storage.url(saved_path)

            logger.info(f"Saved locally: {url}")
            return url

        except Exception as e:
            logger.error(f"Local save failed: {e}", exc_info=True)
            return None

    @classmethod
    def delete_file(cls, url_or_path: str) -> bool:
        """
        Delete a file from storage.
        """
        if cls.is_cloudinary_enabled():
            return cls._delete_from_cloudinary(url_or_path)
        else:
            return cls._delete_locally(url_or_path)

    @classmethod
    def _delete_from_cloudinary(cls, url: str) -> bool:
        """Delete from Cloudinary."""
        try:
            import cloudinary.uploader

            # Extract public_id from URL
            # URL format: https://res.cloudinary.com/{cloud}/image/upload/v{version}/{public_id}.{ext}
            parts = url.split("/upload/")
            if len(parts) > 1:
                public_id = parts[1].rsplit(".", 1)[0]
                # Remove version if present
                if public_id.startswith("v") and "/" in public_id:
                    public_id = public_id.split("/", 1)[1]

                result = cloudinary.uploader.destroy(public_id)
                return result.get("result") == "ok"

            return False

        except Exception as e:
            logger.error(f"Cloudinary delete failed: {e}", exc_info=True)
            return False

    @classmethod
    def _delete_locally(cls, path: str) -> bool:
        """Delete from local filesystem."""
        try:
            from django.core.files.storage import default_storage

            # Extract path from URL if needed
            if path.startswith("/media/"):
                path = path[7:]  # Remove /media/ prefix

            if default_storage.exists(path):
                default_storage.delete(path)
                return True

            return False

        except Exception as e:
            logger.error(f"Local delete failed: {e}", exc_info=True)
            return False
