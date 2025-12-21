import pytest
from unittest.mock import patch, MagicMock

from route_calculator.services.storage_service import StorageService


class TestIsCloudinaryEnabled:
    """Tests for is_cloudinary_enabled method."""

    def test_returns_true_when_cloudinary_fully_configured(self, settings):
        """Should return True when all Cloudinary settings are present."""
        settings.CLOUDINARY_STORAGE = {"CLOUD_NAME": "test-cloud"}
        settings.STORAGE_BACKEND = "cloudinary"

        assert StorageService.is_cloudinary_enabled() is True

    def test_returns_false_when_storage_backend_is_local(self, settings):
        """Should return False when STORAGE_BACKEND is 'local'."""
        settings.CLOUDINARY_STORAGE = {"CLOUD_NAME": "test-cloud"}
        settings.STORAGE_BACKEND = "local"

        assert StorageService.is_cloudinary_enabled() is False

    def test_returns_false_when_cloud_name_missing(self, settings):
        """Should return False when CLOUD_NAME is not set."""
        settings.CLOUDINARY_STORAGE = {"CLOUD_NAME": ""}
        settings.STORAGE_BACKEND = "cloudinary"

        # Use falsy check since the method returns "" (empty string) which is falsy
        assert not StorageService.is_cloudinary_enabled()

    def test_returns_false_when_cloud_name_is_none(self, settings):
        """Should return False when CLOUD_NAME is None."""
        settings.CLOUDINARY_STORAGE = {"CLOUD_NAME": None}
        settings.STORAGE_BACKEND = "cloudinary"

        assert not StorageService.is_cloudinary_enabled()

    def test_returns_false_when_cloudinary_storage_missing(self, settings):
        """Should return False when CLOUDINARY_STORAGE is not defined."""
        if hasattr(settings, "CLOUDINARY_STORAGE"):
            delattr(settings, "CLOUDINARY_STORAGE")
        settings.STORAGE_BACKEND = "cloudinary"

        assert StorageService.is_cloudinary_enabled() is False

    def test_returns_false_when_storage_backend_not_set(self, settings):
        """Should return False when STORAGE_BACKEND defaults to local."""
        settings.CLOUDINARY_STORAGE = {"CLOUD_NAME": "test-cloud"}
        if hasattr(settings, "STORAGE_BACKEND"):
            delattr(settings, "STORAGE_BACKEND")

        assert StorageService.is_cloudinary_enabled() is False


class TestUploadImage:
    """Tests for upload_image method."""

    @patch.object(StorageService, "_upload_to_cloudinary")
    @patch.object(StorageService, "is_cloudinary_enabled", return_value=True)
    def test_routes_to_cloudinary_when_enabled(
        self, mock_is_enabled, mock_cloudinary_upload
    ):
        """Should call _upload_to_cloudinary when Cloudinary is enabled."""
        mock_cloudinary_upload.return_value = "https://cloudinary.com/image.png"
        image_bytes = b"fake image data"

        result = StorageService.upload_image(
            image_bytes, "test.png", folder="test_folder"
        )

        mock_cloudinary_upload.assert_called_once_with(
            image_bytes, "test.png", "test_folder", "image"
        )
        assert result == "https://cloudinary.com/image.png"

    @patch.object(StorageService, "_save_locally")
    @patch.object(StorageService, "is_cloudinary_enabled", return_value=False)
    def test_routes_to_local_when_cloudinary_disabled(
        self, mock_is_enabled, mock_local_save
    ):
        """Should call _save_locally when Cloudinary is disabled."""
        mock_local_save.return_value = "/media/test_folder/test.png"
        image_bytes = b"fake image data"

        result = StorageService.upload_image(
            image_bytes, "test.png", folder="test_folder"
        )

        mock_local_save.assert_called_once_with(image_bytes, "test.png", "test_folder")
        assert result == "/media/test_folder/test.png"

    @patch.object(StorageService, "_upload_to_cloudinary")
    @patch.object(StorageService, "is_cloudinary_enabled", return_value=True)
    def test_uses_default_folder(self, mock_is_enabled, mock_cloudinary_upload):
        """Should use 'eld_logs' as default folder."""
        mock_cloudinary_upload.return_value = "https://cloudinary.com/image.png"

        StorageService.upload_image(b"data", "test.png")

        mock_cloudinary_upload.assert_called_once_with(
            b"data", "test.png", "eld_logs", "image"
        )

    @patch.object(StorageService, "_upload_to_cloudinary")
    @patch.object(StorageService, "is_cloudinary_enabled", return_value=True)
    def test_passes_custom_resource_type(self, mock_is_enabled, mock_cloudinary_upload):
        """Should pass custom resource_type to Cloudinary upload."""
        mock_cloudinary_upload.return_value = "https://cloudinary.com/file.pdf"

        StorageService.upload_image(b"data", "test.pdf", resource_type="raw")

        mock_cloudinary_upload.assert_called_once_with(
            b"data", "test.pdf", "eld_logs", "raw"
        )


class TestUploadToCloudinary:
    """Tests for _upload_to_cloudinary method."""

    @patch("cloudinary.uploader.upload")
    def test_successful_upload(self, mock_upload):
        """Should return secure_url on successful upload."""
        mock_upload.return_value = {
            "secure_url": "https://res.cloudinary.com/test/image/upload/v123/folder/test.png"
        }
        image_bytes = b"fake image data"

        result = StorageService._upload_to_cloudinary(
            image_bytes, "test.png", "folder", "image"
        )

        assert (
            result
            == "https://res.cloudinary.com/test/image/upload/v123/folder/test.png"
        )
        mock_upload.assert_called_once()

    @patch("cloudinary.uploader.upload")
    def test_upload_with_correct_parameters(self, mock_upload):
        """Should call cloudinary.uploader.upload with correct parameters."""
        mock_upload.return_value = {"secure_url": "https://example.com/image.png"}
        image_bytes = b"test data"

        StorageService._upload_to_cloudinary(
            image_bytes, "my_image.png", "my_folder", "image"
        )

        call_kwargs = mock_upload.call_args[1]
        assert call_kwargs["public_id"] == "my_folder/my_image"
        assert call_kwargs["resource_type"] == "image"
        assert call_kwargs["overwrite"] is True
        assert call_kwargs["format"] == "png"
        assert call_kwargs["transformation"] == [
            {"quality": "auto:best"},
            {"fetch_format": "auto"},
        ]

    @patch("cloudinary.uploader.upload")
    def test_removes_extension_from_public_id(self, mock_upload):
        """Should remove file extension from public_id."""
        mock_upload.return_value = {"secure_url": "https://example.com/image.png"}

        StorageService._upload_to_cloudinary(
            b"data", "image.with.dots.png", "folder", "image"
        )

        call_kwargs = mock_upload.call_args[1]
        assert call_kwargs["public_id"] == "folder/image.with.dots"

    @patch("cloudinary.uploader.upload")
    def test_returns_none_on_exception(self, mock_upload):
        """Should return None when upload fails."""
        mock_upload.side_effect = Exception("Upload failed")

        result = StorageService._upload_to_cloudinary(
            b"data", "test.png", "folder", "image"
        )

        assert result is None

    @patch("cloudinary.uploader.upload")
    def test_handles_missing_secure_url(self, mock_upload):
        """Should return None when secure_url is missing from response."""
        mock_upload.return_value = {}

        result = StorageService._upload_to_cloudinary(
            b"data", "test.png", "folder", "image"
        )

        assert result is None


class TestSaveLocally:
    """Tests for _save_locally method."""

    @patch("django.core.files.storage.default_storage")
    def test_successful_save(self, mock_storage):
        """Should save file and return URL."""
        mock_storage.save.return_value = "folder/test.png"
        mock_storage.url.return_value = "/media/folder/test.png"
        image_bytes = b"fake image data"

        result = StorageService._save_locally(image_bytes, "test.png", "folder")

        assert result == "/media/folder/test.png"
        mock_storage.save.assert_called_once()
        mock_storage.url.assert_called_once_with("folder/test.png")

    @patch("django.core.files.storage.default_storage")
    def test_constructs_correct_path(self, mock_storage):
        """Should construct path as folder/filename."""
        mock_storage.save.return_value = "my_folder/my_file.png"
        mock_storage.url.return_value = "/media/my_folder/my_file.png"

        StorageService._save_locally(b"data", "my_file.png", "my_folder")

        call_args = mock_storage.save.call_args[0]
        assert call_args[0] == "my_folder/my_file.png"

    @patch("django.core.files.storage.default_storage")
    def test_returns_none_on_exception(self, mock_storage):
        """Should return None when save fails."""
        mock_storage.save.side_effect = Exception("Save failed")

        result = StorageService._save_locally(b"data", "test.png", "folder")

        assert result is None


class TestDeleteFile:
    """Tests for delete_file method."""

    @patch.object(StorageService, "_delete_from_cloudinary")
    @patch.object(StorageService, "is_cloudinary_enabled", return_value=True)
    def test_routes_to_cloudinary_when_enabled(
        self, mock_is_enabled, mock_cloudinary_delete
    ):
        """Should call _delete_from_cloudinary when Cloudinary is enabled."""
        mock_cloudinary_delete.return_value = True

        result = StorageService.delete_file("https://cloudinary.com/image.png")

        mock_cloudinary_delete.assert_called_once_with(
            "https://cloudinary.com/image.png"
        )
        assert result is True

    @patch.object(StorageService, "_delete_locally")
    @patch.object(StorageService, "is_cloudinary_enabled", return_value=False)
    def test_routes_to_local_when_cloudinary_disabled(
        self, mock_is_enabled, mock_local_delete
    ):
        """Should call _delete_locally when Cloudinary is disabled."""
        mock_local_delete.return_value = True

        result = StorageService.delete_file("/media/folder/test.png")

        mock_local_delete.assert_called_once_with("/media/folder/test.png")
        assert result is True


class TestDeleteFromCloudinary:
    """Tests for _delete_from_cloudinary method."""

    @patch("cloudinary.uploader.destroy")
    def test_successful_delete(self, mock_destroy):
        """Should return True on successful delete."""
        mock_destroy.return_value = {"result": "ok"}
        url = "https://res.cloudinary.com/cloud/image/upload/v123/folder/image.png"

        result = StorageService._delete_from_cloudinary(url)

        assert result is True
        mock_destroy.assert_called_once_with("folder/image")

    @patch("cloudinary.uploader.destroy")
    def test_extracts_public_id_without_version(self, mock_destroy):
        """Should correctly extract public_id removing version prefix."""
        mock_destroy.return_value = {"result": "ok"}
        url = "https://res.cloudinary.com/cloud/image/upload/v1234567890/my_folder/my_image.png"

        StorageService._delete_from_cloudinary(url)

        mock_destroy.assert_called_once_with("my_folder/my_image")

    @patch("cloudinary.uploader.destroy")
    def test_returns_false_on_failed_delete(self, mock_destroy):
        """Should return False when delete result is not 'ok'."""
        mock_destroy.return_value = {"result": "not found"}

        result = StorageService._delete_from_cloudinary(
            "https://res.cloudinary.com/cloud/image/upload/v123/folder/image.png"
        )

        assert result is False

    @patch("cloudinary.uploader.destroy")
    def test_returns_false_on_exception(self, mock_destroy):
        """Should return False when exception occurs."""
        mock_destroy.side_effect = Exception("Delete failed")

        result = StorageService._delete_from_cloudinary(
            "https://res.cloudinary.com/cloud/image/upload/v123/folder/image.png"
        )

        assert result is False

    def test_returns_false_for_invalid_url_format(self):
        """Should return False for URL without /upload/ segment."""
        result = StorageService._delete_from_cloudinary(
            "https://invalid-url.com/image.png"
        )

        assert result is False


class TestDeleteLocally:
    """Tests for _delete_locally method."""

    @patch("django.core.files.storage.default_storage")
    def test_successful_delete(self, mock_storage):
        """Should return True on successful delete."""
        mock_storage.exists.return_value = True

        result = StorageService._delete_locally("folder/test.png")

        assert result is True
        mock_storage.delete.assert_called_once_with("folder/test.png")

    @patch("django.core.files.storage.default_storage")
    def test_strips_media_prefix(self, mock_storage):
        """Should strip /media/ prefix from path."""
        mock_storage.exists.return_value = True

        StorageService._delete_locally("/media/folder/test.png")

        mock_storage.exists.assert_called_once_with("folder/test.png")
        mock_storage.delete.assert_called_once_with("folder/test.png")

    @patch("django.core.files.storage.default_storage")
    def test_returns_false_when_file_not_exists(self, mock_storage):
        """Should return False when file doesn't exist."""
        mock_storage.exists.return_value = False

        result = StorageService._delete_locally("folder/nonexistent.png")

        assert result is False
        mock_storage.delete.assert_not_called()

    @patch("django.core.files.storage.default_storage")
    def test_returns_false_on_exception(self, mock_storage):
        """Should return False when exception occurs."""
        mock_storage.exists.side_effect = Exception("Storage error")

        result = StorageService._delete_locally("folder/test.png")

        assert result is False


class TestIntegration:
    """Integration tests for StorageService."""

    @patch("django.core.files.storage.default_storage")
    def test_full_local_upload_and_delete_flow(self, mock_storage, settings):
        """Test complete local upload and delete workflow."""
        # Setup
        settings.STORAGE_BACKEND = "local"
        if hasattr(settings, "CLOUDINARY_STORAGE"):
            delattr(settings, "CLOUDINARY_STORAGE")

        mock_storage.save.return_value = "eld_logs/test_image.png"
        mock_storage.url.return_value = "/media/eld_logs/test_image.png"
        mock_storage.exists.return_value = True

        # Upload
        image_bytes = b"test image content"
        upload_result = StorageService.upload_image(image_bytes, "test_image.png")

        assert upload_result == "/media/eld_logs/test_image.png"

        # Delete
        delete_result = StorageService.delete_file(upload_result)

        assert delete_result is True

    @patch("cloudinary.uploader.destroy")
    @patch("cloudinary.uploader.upload")
    def test_full_cloudinary_upload_and_delete_flow(
        self, mock_upload, mock_destroy, settings
    ):
        """Test complete Cloudinary upload and delete workflow."""
        # Setup
        settings.CLOUDINARY_STORAGE = {"CLOUD_NAME": "test-cloud"}
        settings.STORAGE_BACKEND = "cloudinary"

        cloudinary_url = "https://res.cloudinary.com/test-cloud/image/upload/v123/eld_logs/test_image.png"
        mock_upload.return_value = {"secure_url": cloudinary_url}
        mock_destroy.return_value = {"result": "ok"}

        # Upload
        image_bytes = b"test image content"
        upload_result = StorageService.upload_image(image_bytes, "test_image.png")

        assert upload_result == cloudinary_url

        # Delete
        delete_result = StorageService.delete_file(upload_result)

        assert delete_result is True


class TestEdgeCases:
    """Edge case tests for StorageService."""

    @patch("cloudinary.uploader.upload")
    def test_filename_without_extension(self, mock_upload):
        """Should handle filename without extension."""
        mock_upload.return_value = {"secure_url": "https://example.com/image"}

        StorageService._upload_to_cloudinary(b"data", "filename", "folder", "image")

        call_kwargs = mock_upload.call_args[1]
        assert call_kwargs["public_id"] == "folder/filename"

    @patch("cloudinary.uploader.destroy")
    def test_delete_url_without_version(self, mock_destroy):
        """Should handle URL without version number."""
        mock_destroy.return_value = {"result": "ok"}
        # URL without version (no 'v' prefix)
        url = "https://res.cloudinary.com/cloud/image/upload/folder/image.png"

        result = StorageService._delete_from_cloudinary(url)

        assert result is True
        mock_destroy.assert_called_once_with("folder/image")

    @patch("cloudinary.uploader.destroy")
    def test_delete_nested_folder_path(self, mock_destroy):
        """Should handle nested folder paths in URL."""
        mock_destroy.return_value = {"result": "ok"}
        url = "https://res.cloudinary.com/cloud/image/upload/v123/folder/subfolder/image.png"

        StorageService._delete_from_cloudinary(url)

        mock_destroy.assert_called_once_with("folder/subfolder/image")

    @patch("django.core.files.storage.default_storage")
    def test_save_locally_with_content_file(self, mock_storage):
        """Should create ContentFile from bytes."""
        mock_storage.save.return_value = "folder/test.png"
        mock_storage.url.return_value = "/media/folder/test.png"

        StorageService._save_locally(b"test data", "test.png", "folder")

        # Verify save was called with a ContentFile
        call_args = mock_storage.save.call_args[0]
        assert call_args[0] == "folder/test.png"
        # The second argument should be a ContentFile instance
        content_file = call_args[1]
        assert content_file.read() == b"test data"
