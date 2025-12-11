"""
Storage service for file operations.

Supports both MinIO/S3 and local filesystem storage.
Falls back to local storage if MinIO is not available.
"""

import io
import os
import shutil
import logging
from pathlib import Path
from typing import BinaryIO, Optional
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)


class LocalStorageService:
    """
    Local filesystem storage service.
    
    Used for development when MinIO/S3 is not available.
    """
    
    def __init__(self, base_path: str = None) -> None:
        """Initialize local storage."""
        self.base_path = Path(base_path or os.environ.get(
            "LOCAL_STORAGE_PATH", 
            Path(__file__).parent.parent.parent.parent / "data" / "uploads"
        ))
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using local storage at: {self.base_path}")
    
    def generate_file_key(self, user_id: int, filename: str) -> str:
        """Generate unique file key."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        return f"uploads/{user_id}/{timestamp}_{filename}"
    
    def upload_file(
        self,
        file_data: BinaryIO,
        file_key: str,
        content_type: str,
        file_size: int,
    ) -> str:
        """Upload file to local storage."""
        file_path = self.base_path / file_key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file_data, f)
        
        logger.info(f"File saved locally: {file_path}")
        return file_key
    
    def delete_file(self, file_key: str) -> None:
        """Delete file from local storage."""
        file_path = self.base_path / file_key
        if file_path.exists():
            file_path.unlink()
            logger.info(f"File deleted: {file_path}")
    
    def get_file(self, file_key: str) -> Optional[bytes]:
        """Get file content."""
        file_path = self.base_path / file_key
        if file_path.exists():
            return file_path.read_bytes()
        return None


class MinIOStorageService:
    """
    MinIO/S3 object storage service.
    
    Used for production with cloud storage.
    """
    
    def __init__(self) -> None:
        """Initialize MinIO client."""
        from minio import Minio
        
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False,
        )
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self) -> None:
        """Create bucket if it doesn't exist."""
        from minio.error import S3Error
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except S3Error as e:
            raise RuntimeError(f"Failed to create bucket: {e}")
    
    def generate_file_key(self, user_id: int, filename: str) -> str:
        """Generate unique file key."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        return f"uploads/{user_id}/{timestamp}_{filename}"
    
    def upload_file(
        self,
        file_data: BinaryIO,
        file_key: str,
        content_type: str,
        file_size: int,
    ) -> str:
        """Upload file to MinIO."""
        from minio.error import S3Error
        try:
            self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=file_key,
                data=file_data,
                length=file_size,
                content_type=content_type,
            )
            return file_key
        except S3Error as e:
            raise RuntimeError(f"Failed to upload file: {e}")
    
    def delete_file(self, file_key: str) -> None:
        """Delete file from MinIO."""
        from minio.error import S3Error
        try:
            self.client.remove_object(
                bucket_name=self.bucket_name,
                object_name=file_key,
            )
        except S3Error as e:
            raise RuntimeError(f"Failed to delete file: {e}")


def get_storage_service():
    """
    Get the appropriate storage service.
    
    Tries MinIO first, falls back to local storage.
    """
    # Check if we should use local storage
    use_local = os.environ.get("STORAGE_TYPE", "").lower() == "local"
    
    if use_local:
        logger.info("Using local file storage")
        return LocalStorageService()
    
    # Try MinIO
    try:
        service = MinIOStorageService()
        logger.info("Using MinIO storage")
        return service
    except Exception as e:
        logger.warning(f"MinIO not available ({e}), falling back to local storage")
        return LocalStorageService()


# Lazy-loaded singleton
_storage_service = None

def _get_storage():
    global _storage_service
    if _storage_service is None:
        _storage_service = get_storage_service()
    return _storage_service


class StorageServiceProxy:
    """Proxy that lazy-loads the actual storage service."""
    
    def generate_file_key(self, user_id: int, filename: str) -> str:
        return _get_storage().generate_file_key(user_id, filename)
    
    def upload_file(self, file_data: BinaryIO, file_key: str, content_type: str, file_size: int) -> str:
        return _get_storage().upload_file(file_data, file_key, content_type, file_size)
    
    def delete_file(self, file_key: str) -> None:
        return _get_storage().delete_file(file_key)


# Singleton proxy instance (doesn't connect until first use)
storage_service = StorageServiceProxy()

# Alias for backwards compatibility
StorageService = StorageServiceProxy
