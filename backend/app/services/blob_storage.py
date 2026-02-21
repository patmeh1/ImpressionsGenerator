"""Azure Blob Storage service for file management."""

import logging
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, ContentSettings

from app.config import settings

logger = logging.getLogger(__name__)


class BlobStorageService:
    """Manages file operations in Azure Blob Storage."""

    def __init__(self) -> None:
        self._client: BlobServiceClient | None = None
        self._container_name = settings.BLOB_CONTAINER_NAME

    async def initialize(self) -> None:
        """Initialize Blob Storage client and ensure container exists."""
        credential = DefaultAzureCredential()
        self._client = BlobServiceClient(
            account_url=settings.BLOB_STORAGE_ACCOUNT_URL,
            credential=credential,
        )
        container_client = self._client.get_container_client(self._container_name)
        if not container_client.exists():
            container_client.create_container()
            logger.info("Created blob container '%s'", self._container_name)

        logger.info("Blob Storage initialized")

    def _get_blob_path(self, doctor_id: str, file_name: str) -> str:
        """Build a blob path with doctor_id prefix for tenant isolation."""
        return f"{doctor_id}/{file_name}"

    async def upload_file(
        self,
        doctor_id: str,
        file_name: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        """Upload a file to blob storage."""
        if self._client is None:
            raise RuntimeError("BlobStorageService not initialized")

        blob_path = self._get_blob_path(doctor_id, file_name)
        blob_client = self._client.get_blob_client(
            container=self._container_name, blob=blob_path
        )
        blob_client.upload_blob(
            content,
            overwrite=True,
            content_settings=ContentSettings(content_type=content_type),
        )
        logger.info("Uploaded blob '%s'", blob_path)
        return {
            "blob_path": blob_path,
            "file_name": file_name,
            "size": len(content),
            "url": blob_client.url,
        }

    async def download_file(self, doctor_id: str, file_name: str) -> bytes:
        """Download a file from blob storage."""
        if self._client is None:
            raise RuntimeError("BlobStorageService not initialized")

        blob_path = self._get_blob_path(doctor_id, file_name)
        blob_client = self._client.get_blob_client(
            container=self._container_name, blob=blob_path
        )
        stream = blob_client.download_blob()
        data = stream.readall()
        logger.info("Downloaded blob '%s' (%d bytes)", blob_path, len(data))
        return data

    async def delete_file(self, doctor_id: str, file_name: str) -> bool:
        """Delete a file from blob storage."""
        if self._client is None:
            raise RuntimeError("BlobStorageService not initialized")

        blob_path = self._get_blob_path(doctor_id, file_name)
        blob_client = self._client.get_blob_client(
            container=self._container_name, blob=blob_path
        )
        try:
            blob_client.delete_blob()
            logger.info("Deleted blob '%s'", blob_path)
            return True
        except Exception:
            logger.warning("Blob '%s' not found for deletion", blob_path)
            return False

    async def list_files(self, doctor_id: str) -> list[dict[str, Any]]:
        """List all files for a specific doctor."""
        if self._client is None:
            raise RuntimeError("BlobStorageService not initialized")

        container_client = self._client.get_container_client(self._container_name)
        prefix = f"{doctor_id}/"
        blobs = container_client.list_blobs(name_starts_with=prefix)

        files = []
        for blob in blobs:
            files.append({
                "name": blob.name.removeprefix(prefix),
                "blob_path": blob.name,
                "size": blob.size,
                "last_modified": blob.last_modified.isoformat() if blob.last_modified else None,
            })
        return files


# Singleton instance
blob_service = BlobStorageService()
