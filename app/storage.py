"""Storage backend for assets with S3, R2, and local support."""

import os
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union, BinaryIO
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
from app.config import settings
from loguru import logger


class VaultStorageBackend:
    """Vault storage backend with multi-driver support for R2/S3/local."""
    
    def __init__(self):
        self.driver = settings.storage_driver
        self.bucket = settings.storage_bucket
        self.public_base = settings.storage_public_base
        self.signing_ttl = settings.storage_signing_ttl_s
        
        # Check if we have credentials for cloud storage
        self.has_credentials = self._check_credentials()
        
        if not self.has_credentials:
            logger.warning(f"Missing credentials for {self.driver} storage - operating in dry mode")
            self.driver = "local"  # Fallback to local for dry mode
        
        if self.driver in ["r2", "s3"]:
            self._init_cloud()
        else:
            self._init_local()
    
    def _check_credentials(self) -> bool:
        """Check if we have the necessary credentials for cloud storage."""
        if self.driver == "r2":
            return all([
                settings.r2_account_id,
                settings.r2_access_key_id,
                settings.r2_secret_access_key
            ])
        elif self.driver == "s3":
            return all([
                settings.s3_access_key,
                settings.s3_secret_key,
                settings.s3_endpoint
            ])
        return True  # Local doesn't need credentials
    
    def _init_cloud(self):
        """Initialize cloud storage client (R2 or S3)."""
        if self.driver == "r2":
            # Cloudflare R2 uses S3-compatible API
            endpoint_url = f"https://{settings.r2_account_id}.r2.cloudflarestorage.com"
            self.s3_client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=settings.r2_access_key_id,
                aws_secret_access_key=settings.r2_secret_access_key,
                region_name='auto'  # R2 uses 'auto' region
            )
            logger.info(f"Initialized R2 storage with bucket: {self.bucket}")
        else:  # s3
            self.s3_client = boto3.client(
                's3',
                region_name=settings.s3_region,
                endpoint_url=settings.s3_endpoint,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key
            )
            logger.info(f"Initialized S3 storage with bucket: {self.bucket}")
    
    def _init_local(self):
        """Initialize local file storage."""
        self.base_path = Path("./data/vault")
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized local storage backend at: {self.base_path}")
    
    def generate_storage_key(self, tenant_id: str, persona_id: str, filename: str) -> str:
        """Generate storage key using format: tenant_id/yyyy/mm/persona_id/filename"""
        now = datetime.utcnow()
        return f"{tenant_id}/{now.year}/{now.month:02d}/{persona_id}/{filename}"
    
    def put_object(self, tenant_id: str, storage_key: str, data: Union[bytes, BinaryIO], mime: str, dry_run: bool = False) -> Dict[str, Any]:
        """Store object and return storage info."""
        if dry_run or not self.has_credentials:
            # Return mock URLs for dry run
            public_url = f"{settings.public_base_url}/cdn/mock/{storage_key}"
            return {
                "storage_key": storage_key,
                "public_url": public_url,
                "dry_run": True
            }
        
        try:
            if self.driver in ["r2", "s3"]:
                success = self._put_cloud(storage_key, data, mime)
                if success:
                    public_url = f"{self.public_base}/cdn/{storage_key}"
                    return {
                        "storage_key": storage_key,
                        "public_url": public_url
                    }
                else:
                    raise Exception("Cloud storage failed")
            else:
                success = self._put_local(storage_key, data)
                if success:
                    public_url = f"{settings.public_base_url}/cdn/{storage_key}"
                    return {
                        "storage_key": storage_key,
                        "public_url": public_url
                    }
                else:
                    raise Exception("Local storage failed")
        except Exception as e:
            logger.error(f"Failed to store object {storage_key}: {e}")
            raise e
    
    def sign_get(self, storage_key: str, ttl_s: Optional[int] = None, dry_run: bool = False) -> Dict[str, Any]:
        """Generate signed URL for object access."""
        if ttl_s is None:
            ttl_s = self.signing_ttl
        
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_s)
        
        if dry_run or not self.has_credentials:
            # Return mock signed URL for dry run
            signed_url = f"{settings.public_base_url}/cdn/mock/{storage_key}?expires={int(expires_at.timestamp())}&sig=mock"
            return {
                "signed_url": signed_url,
                "expires_at": expires_at.isoformat() + "Z"
            }
        
        try:
            if self.driver in ["r2", "s3"]:
                signed_url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket, 'Key': storage_key},
                    ExpiresIn=ttl_s
                )
                return {
                    "signed_url": signed_url,
                    "expires_at": expires_at.isoformat() + "Z"
                }
            else:
                # For local storage, return regular URL (no signing needed)
                public_url = f"{settings.public_base_url}/cdn/{storage_key}"
                return {
                    "signed_url": public_url,
                    "expires_at": expires_at.isoformat() + "Z"
                }
        except Exception as e:
            logger.error(f"Failed to generate signed URL for {storage_key}: {e}")
            raise e
    
    def head(self, storage_key: str, dry_run: bool = False) -> Dict[str, Any]:
        """Get object metadata without downloading."""
        if dry_run or not self.has_credentials:
            return {
                "size_bytes": 12345,
                "mime": "application/octet-stream",
                "exists": True,
                "dry_run": True
            }
        
        try:
            if self.driver in ["r2", "s3"]:
                response = self.s3_client.head_object(Bucket=self.bucket, Key=storage_key)
                return {
                    "size_bytes": response.get('ContentLength', 0),
                    "mime": response.get('ContentType', 'application/octet-stream'),
                    "exists": True
                }
            else:
                file_path = self.base_path / storage_key
                if file_path.exists():
                    stat = file_path.stat()
                    mime = self._get_content_type(str(file_path))
                    return {
                        "size_bytes": stat.st_size,
                        "mime": mime,
                        "exists": True
                    }
                else:
                    return {
                        "size_bytes": 0,
                        "mime": "",
                        "exists": False
                    }
        except Exception as e:
            logger.error(f"Failed to get head for {storage_key}: {e}")
            return {
                "size_bytes": 0,
                "mime": "",
                "exists": False,
                "error": str(e)
            }
    
    def _put_cloud(self, storage_key: str, data: Union[bytes, BinaryIO], mime: str) -> bool:
        """Store data in cloud storage (R2 or S3)."""
        try:
            # Convert data to bytes if needed
            if hasattr(data, 'read') and callable(getattr(data, 'read')):
                data_bytes = data.read()  # type: ignore
            else:
                data_bytes = data  # type: ignore
            
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=storage_key,
                Body=data_bytes,
                ContentType=mime
            )
            logger.info(f"Stored {len(data_bytes)} bytes to {self.driver}: {storage_key}")
            return True
        except ClientError as e:
            logger.error(f"{self.driver} put_object failed for {storage_key}: {e}")
            return False
    
    def _put_local(self, storage_key: str, data: Union[bytes, BinaryIO]) -> bool:
        """Store data locally."""
        file_path = self.base_path / storage_key
        
        # Create parent directories
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            # Convert data to bytes if needed
            if hasattr(data, 'read') and callable(getattr(data, 'read')):
                data_bytes = data.read()  # type: ignore
            else:
                data_bytes = data  # type: ignore
            
            with open(file_path, 'wb') as f:
                f.write(data_bytes)
            logger.info(f"Stored {len(data_bytes)} bytes locally: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Local file write failed for {file_path}: {e}")
            return False
    
    def _get_content_type(self, path: str) -> str:
        """Get content type based on file extension."""
        ext = Path(path).suffix.lower()
        content_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.webp': 'image/webp',
            '.gif': 'image/gif',
            '.pdf': 'application/pdf',
            '.json': 'application/json',
            '.txt': 'text/plain'
        }
        return content_types.get(ext, 'application/octet-stream')


# Utility functions for vault operations
def calculate_sha256(data: bytes) -> str:
    """Calculate SHA256 hash of data."""
    return hashlib.sha256(data).hexdigest()


def get_file_extension(mime_type: str) -> str:
    """Get file extension from MIME type."""
    mime_to_ext = {
        'image/png': 'png',
        'image/jpeg': 'jpg',
        'image/webp': 'webp',
        'application/pdf': 'pdf',
        'text/plain': 'txt'
    }
    return mime_to_ext.get(mime_type, 'bin')


def is_valid_vault_mime(mime_type: str) -> bool:
    """Check if MIME type is allowed in vault."""
    # MIME allowlist as specified in vault requirements
    allowed_types = {
        'image/png',
        'image/jpeg', 
        'image/webp',
        'application/pdf',
        'text/plain'
    }
    return mime_type in allowed_types


def validate_file_size(size_bytes: int, max_mb: Optional[int] = None) -> bool:
    """Validate file size against limits."""
    if max_mb is None:
        max_mb = settings.storage_max_mb
    
    max_bytes = max_mb * 1024 * 1024
    return size_bytes <= max_bytes


# Global vault storage instance
vault_storage = VaultStorageBackend()

# Backwards compatibility for existing code
storage = vault_storage  # Alias for existing imports

def is_valid_image_mime(mime_type: str) -> bool:
    """Check if MIME type is a valid image format (backwards compatibility)."""
    valid_types = {'image/png', 'image/jpeg', 'image/webp', 'image/gif'}
    return mime_type in valid_types