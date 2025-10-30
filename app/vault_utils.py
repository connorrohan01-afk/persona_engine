"""Vault utility functions for PersonaEngine."""

import re
import base64
from datetime import datetime, timedelta
from typing import Optional, Tuple
from pathlib import Path
from app.storage import calculate_sha256, is_valid_vault_mime, validate_file_size


def normalize_filename(filename: str) -> str:
    """Normalize filename for safe storage."""
    # Remove any directory traversal attempts
    filename = Path(filename).name
    
    # Replace unsafe characters with underscores
    safe_filename = re.sub(r'[^\w\-_.]', '_', filename)
    
    # Remove multiple consecutive underscores/dots
    safe_filename = re.sub(r'[_.]{2,}', '_', safe_filename)
    
    # Ensure we have an extension
    if '.' not in safe_filename:
        safe_filename += '.bin'
    
    # Limit length to 100 characters
    if len(safe_filename) > 100:
        name, ext = safe_filename.rsplit('.', 1)
        safe_filename = name[:95] + '.' + ext
    
    return safe_filename


def decode_base64_content(base64_data: str) -> Tuple[bytes, str]:
    """Decode base64 content and return bytes with error information."""
    try:
        # Remove data URL prefix if present (e.g., "data:image/png;base64,")
        if base64_data.startswith('data:'):
            base64_data = base64_data.split(',', 1)[1]
        
        # Decode base64
        content_bytes = base64.b64decode(base64_data)
        return content_bytes, ""
    
    except Exception as e:
        return b"", f"Invalid base64 data: {str(e)}"


def validate_vault_content(
    content: bytes, 
    mime: str, 
    max_mb: Optional[int] = None
) -> Tuple[bool, str]:
    """Validate vault content against all requirements."""
    
    # Check MIME type allowlist
    if not is_valid_vault_mime(mime):
        return False, "mime_not_allowed"
    
    # Check file size
    if not validate_file_size(len(content), max_mb):
        return False, "too_large"
    
    # Basic content validation
    if len(content) == 0:
        return False, "empty_file"
    
    return True, ""


def generate_ttl_datetime(ttl_s: int) -> datetime:
    """Generate expiration datetime from TTL in seconds."""
    return datetime.utcnow() + timedelta(seconds=ttl_s)


def is_nsfw_content(name: str, mime: str = None) -> bool:
    """Basic NSFW content detection based on filename patterns."""
    nsfw_patterns = [
        r'\b(adult|nsfw|xxx|porn|sex|nude|naked)\b',
        r'\b(erotic|explicit|mature)\b',
        r'\b18\+',
    ]
    
    name_lower = name.lower()
    for pattern in nsfw_patterns:
        if re.search(pattern, name_lower):
            return True
    
    return False


def get_content_hash_prefix(sha256_hash: str, length: int = 16) -> str:
    """Get a prefix of the SHA256 hash for deduplication checks."""
    return sha256_hash[:length]


def generate_claim_url(claim_code: str, base_url: str) -> str:
    """Generate claim URL for a vault link."""
    return f"{base_url}/api/v1/vaults/claim/{claim_code}"


def validate_tenant_access(tenant_id: str, user_tenant: str) -> bool:
    """Validate tenant access permissions."""
    # Simple tenant validation - same tenant or owner
    return tenant_id == user_tenant or user_tenant == "owner"


def should_send_as_file(mime: str, nsfw: bool) -> bool:
    """Determine if content should be sent as file vs inline in Telegram."""
    # Send as file if NSFW to avoid inline preview
    if nsfw:
        return True
    
    # Send non-images as files
    if not mime.startswith('image/'):
        return True
    
    return False


def extract_file_info(filename: str, mime: str) -> dict:
    """Extract file information for metadata."""
    file_path = Path(filename)
    
    return {
        "name": file_path.stem,
        "extension": file_path.suffix.lstrip('.'),
        "full_name": filename,
        "is_image": mime.startswith('image/'),
        "is_document": mime == 'application/pdf',
        "is_text": mime == 'text/plain'
    }


def calculate_storage_usage(tenant_id: str, items: list) -> dict:
    """Calculate storage usage statistics for a tenant."""
    total_bytes = sum(item.size_bytes for item in items if hasattr(item, 'size_bytes'))
    total_mb = round(total_bytes / (1024 * 1024), 2)
    
    # Count by type
    type_counts = {}
    for item in items:
        if hasattr(item, 'kind'):
            type_counts[item.kind] = type_counts.get(item.kind, 0) + 1
    
    return {
        "tenant_id": tenant_id,
        "total_items": len(items),
        "total_bytes": total_bytes,
        "total_mb": total_mb,
        "by_type": type_counts
    }