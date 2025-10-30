"""Vault Storage & Delivery API Routes for PersonaEngine."""

import secrets
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import uuid4
from sqlalchemy import desc

from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form, Header
from fastapi.responses import JSONResponse, RedirectResponse
from sqlmodel import Session, select, or_, and_

from app.db import get_session
from app.security import verify_token, require_tenant_access
from app.models_vaults import VaultItem, VaultLink, VaultAccessLog, VaultItemKind, VaultAccessChannel, VaultAccessAction
from app.storage import vault_storage, calculate_sha256, is_valid_vault_mime, validate_file_size
from app.vault_utils import (
    normalize_filename, decode_base64_content, validate_vault_content,
    generate_ttl_datetime, is_nsfw_content, should_send_as_file, 
    extract_file_info, calculate_storage_usage
)
from app.config import settings
from app.models import Account

# Router for vault endpoints
vault_router = APIRouter(prefix="/api/v1/vaults", tags=["Vault Storage"])


# === VAULT ITEM ENDPOINTS ===

@vault_router.post("/items", response_model=Dict[str, Any])
def create_vault_item(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    kind: str = Form("file"),
    public: bool = Form(False),
    nsfw: bool = Form(False),
    session: Session = Depends(get_session),
    validated_tenant_id: str = Depends(require_tenant_access)
):
    """Create a new vault item by uploading a file."""
    
    # Use validated tenant ID
    tenant_id = validated_tenant_id
    
    # Read file content
    try:
        content = file.file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file")
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to read file")
    
    # Validate MIME type
    mime_type = file.content_type or "application/octet-stream"
    if not is_valid_vault_mime(mime_type):
        raise HTTPException(status_code=400, detail="File type not allowed")
    
    # Validate file size
    if not validate_file_size(len(content)):
        raise HTTPException(
            status_code=413, 
            detail=f"File too large (max {settings.storage_max_mb}MB)"
        )
    
    # Calculate content hash
    content_hash = calculate_sha256(content)
    
    # Check for existing content by hash (deduplication)
    existing = session.exec(
        select(VaultItem).where(
            and_(
                VaultItem.tenant_id == tenant_id,
                VaultItem.sha256 == content_hash
            )
        )
    ).first()
    
    if existing:
        return {
            "success": True,
            "item_id": str(existing.id),
            "message": "File already exists (deduplicated)",
            "existing": True
        }
    
    # Normalize filename
    filename = normalize_filename(name or file.filename or f"upload_{uuid4().hex[:8]}")
    
    # Auto-detect NSFW content
    if not nsfw:
        nsfw = is_nsfw_content(filename, mime_type)
    
    # Store content
    item_id = str(uuid4())
    storage_key = f"{tenant_id}/{item_id[:2]}/{item_id[2:]}"
    
    result = vault_storage.put_object(tenant_id, storage_key, content, mime_type)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to store file")
    
    # Create vault item record
    vault_item = VaultItem(
        tenant_id=tenant_id,
        persona_id="default",  # TODO: get from request or user context
        name=filename,
        kind=VaultItemKind(kind),  # Convert string to enum
        mime=mime_type,
        size_bytes=len(content),
        sha256=content_hash,
        storage_key=storage_key,
        public_url=result.get("public_url"),  # Store the public URL from storage
        nsfw=nsfw
    )
    
    session.add(vault_item)
    session.commit()
    session.refresh(vault_item)
    
    return {
        "success": True,
        "item_id": str(vault_item.id),
        "name": vault_item.name,
        "size_bytes": vault_item.size_bytes,
        "storage_key": vault_item.storage_key,
        "existing": False
    }


@vault_router.post("/items/base64", response_model=Dict[str, Any])
def create_vault_item_base64(
    content: str = Form(...),
    name: str = Form(...),
    mime_type: str = Form(...),
    description: Optional[str] = Form(None),
    kind: str = Form("file"),
    public: bool = Form(False),
    nsfw: bool = Form(False),
    session: Session = Depends(get_session),
    validated_tenant_id: str = Depends(require_tenant_access)
):
    """Create a new vault item from base64 content."""
    
    # Use validated tenant ID
    tenant_id = validated_tenant_id
    
    # Decode base64 content
    content_bytes, error = decode_base64_content(content)
    if error:
        raise HTTPException(status_code=400, detail=error)
    
    # Validate content and MIME type
    valid, error = validate_vault_content(content_bytes, mime_type)
    if not valid:
        raise HTTPException(status_code=400, detail=f"Invalid content: {error}")
    
    # Calculate content hash
    content_hash = calculate_sha256(content_bytes)
    
    # Check for existing content by hash (deduplication)
    existing = session.exec(
        select(VaultItem).where(
            and_(
                VaultItem.tenant_id == tenant_id,
                VaultItem.sha256 == content_hash
            )
        )
    ).first()
    
    if existing:
        return {
            "success": True,
            "item_id": str(existing.id),
            "message": "Content already exists (deduplicated)",
            "existing": True
        }
    
    # Normalize filename
    filename = normalize_filename(name)
    
    # Auto-detect NSFW content
    if not nsfw:
        nsfw = is_nsfw_content(filename, mime_type)
    
    # Store content
    item_id = str(uuid4())
    storage_key = f"{tenant_id}/{item_id[:2]}/{item_id[2:]}"
    
    result = vault_storage.put_object(tenant_id, storage_key, content_bytes, mime_type)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to store content")
    
    # Create vault item record
    vault_item = VaultItem(
        tenant_id=tenant_id,
        persona_id="default",  # TODO: get from request or user context
        name=filename,
        kind=VaultItemKind(kind),  # Convert string to enum
        mime=mime_type,
        size_bytes=len(content_bytes),
        sha256=content_hash,
        storage_key=storage_key,
        public_url=result.get("public_url"),  # Store the public URL from storage
        nsfw=nsfw
    )
    
    session.add(vault_item)
    session.commit()
    session.refresh(vault_item)
    
    return {
        "success": True,
        "item_id": str(vault_item.id),
        "name": vault_item.name,
        "size_bytes": vault_item.size_bytes,
        "storage_key": vault_item.storage_key,
        "existing": False
    }


@vault_router.get("/items", response_model=List[Dict[str, Any]])
def list_vault_items(
    kind: Optional[str] = None,
    public_only: bool = False,
    include_nsfw: bool = False,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    validated_tenant_id: str = Depends(require_tenant_access)
):
    """List vault items for a tenant."""
    
    # Use validated tenant ID
    tenant_id = validated_tenant_id
    
    # Build query
    query = select(VaultItem).where(VaultItem.tenant_id == tenant_id)
    
    if kind:
        from app.models_vaults import VaultItemKind
        query = query.where(VaultItem.kind == VaultItemKind(kind))
    
    # Note: VaultItem model doesn't have a 'public' field, skipping public_only filter
    # if public_only:
    #     query = query.where(VaultItem.public_url.isnot(None))
    
    if not include_nsfw:
        query = query.where(VaultItem.nsfw == False)
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    items = session.exec(query).all()
    
    return [
        {
            "id": str(item.id),
            "name": item.name,
            "kind": item.kind.value,  # Enum value
            "mime": item.mime,
            "size_bytes": item.size_bytes,
            "nsfw": item.nsfw,
            "created_at": item.created_at.isoformat()
        }
        for item in items
    ]


@vault_router.get("/items/{item_id}", response_model=Dict[str, Any])
def get_vault_item(
    item_id: int,
    session: Session = Depends(get_session),
    validated_tenant_id: str = Depends(require_tenant_access)
):
    """Get vault item details."""
    
    item = session.get(VaultItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Vault item not found")
    
    # Validate tenant access
    if item.tenant_id != validated_tenant_id:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: Item does not belong to specified tenant"
        )
    
    return {
        "id": str(item.id),
        "tenant_id": item.tenant_id,
        "persona_id": item.persona_id,
        "name": item.name,
        "kind": item.kind.value,  # Enum value
        "mime": item.mime,
        "size_bytes": item.size_bytes,
        "sha256": item.sha256,
        "storage_key": item.storage_key,
        "public_url": item.public_url,
        "nsfw": item.nsfw,
        "created_at": item.created_at.isoformat()
    }


@vault_router.delete("/items/{item_id}")
def delete_vault_item(
    item_id: int,
    session: Session = Depends(get_session),
    validated_tenant_id: str = Depends(require_tenant_access)
):
    """Delete a vault item."""
    
    item = session.get(VaultItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Vault item not found")
    
    # Validate tenant access
    if item.tenant_id != validated_tenant_id:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: Item does not belong to specified tenant"
        )
    
    # Delete from storage (using head to check existence first)
    storage_info = vault_storage.head(item.storage_key)
    if storage_info.get("exists"):
        # For cloud storage, we'd need a delete method - for now just log
        from loguru import logger
        logger.info(f"Would delete storage key: {item.storage_key}")
    
    # Delete from database
    session.delete(item)
    session.commit()
    
    return {"success": True, "message": "Vault item deleted"}


# === VAULT LINK ENDPOINTS ===

@vault_router.post("/items/{item_id}/links", response_model=Dict[str, Any])
def create_vault_link(
    item_id: int,
    ttl_s: int = Form(3600),  # 1 hour default
    max_uses: Optional[int] = Form(1),
    session: Session = Depends(get_session),
    validated_tenant_id: str = Depends(require_tenant_access)
):
    """Create a claim link for a vault item."""
    
    # Validate vault item exists
    item = session.get(VaultItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Vault item not found")
    
    # Validate tenant access
    if item.tenant_id != validated_tenant_id:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: Item does not belong to specified tenant"
        )
    
    # Generate claim code
    claim_code = secrets.token_urlsafe(32)
    
    # Calculate expiration
    expires_at = generate_ttl_datetime(ttl_s)
    
    # Create vault link
    # Ensure item.id is not None (should never happen for persisted items)
    if item.id is None:
        raise HTTPException(status_code=500, detail="Invalid item ID")
    
    vault_link = VaultLink(
        tenant_id=item.tenant_id,
        vault_item_id=item.id,
        claim_code=claim_code,
        expires_at=expires_at,
        max_uses=max_uses or 1
    )
    
    session.add(vault_link)
    session.commit()
    session.refresh(vault_link)
    
    return {
        "success": True,
        "link_id": str(vault_link.id),
        "claim_code": vault_link.claim_code,
        "claim_url": f"{settings.public_base_url}/api/v1/vaults/claim/{claim_code}",
        "expires_at": vault_link.expires_at.isoformat(),
        "max_uses": vault_link.max_uses
    }


@vault_router.get("/links", response_model=List[Dict[str, Any]])
def list_vault_links(
    active_only: bool = True,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    validated_tenant_id: str = Depends(require_tenant_access)
):
    """List vault links for a tenant."""
    
    # Use validated tenant ID
    tenant_id = validated_tenant_id
    
    # Join with vault items to filter by tenant
    query = select(VaultLink).join(VaultItem).where(
        and_(
            VaultItem.id == VaultLink.vault_item_id,
            VaultItem.tenant_id == tenant_id
        )
    )
    
    if active_only:
        now = datetime.utcnow()
        query = query.where(
            and_(
                VaultLink.expires_at > now,
                or_(
                    VaultLink.max_uses.is_(None),
                    VaultLink.used_count < VaultLink.max_uses
                )
            )
        )
    
    query = query.offset(offset).limit(limit)
    links = session.exec(query).all()
    
    return [
        {
            "id": str(link.id),
            "vault_item_id": str(link.vault_item_id),
            "claim_code": link.claim_code,
            "expires_at": link.expires_at.isoformat(),
            "max_uses": link.max_uses,
            "used_count": link.used_count,
            "created_at": link.created_at.isoformat()
        }
        for link in links
    ]


@vault_router.delete("/links/{link_id}")
def delete_vault_link(
    link_id: int,
    session: Session = Depends(get_session),
    validated_tenant_id: str = Depends(require_tenant_access)
):
    """Delete/deactivate a vault link."""
    
    link = session.get(VaultLink, link_id)
    if not link:
        raise HTTPException(status_code=404, detail="Vault link not found")
    
    # Get the vault item to validate tenant access
    item = session.get(VaultItem, link.vault_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Associated vault item not found")
    
    # Validate tenant access
    if item.tenant_id != validated_tenant_id:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: Link does not belong to specified tenant"
        )
    
    session.delete(link)
    session.commit()
    
    return {"success": True, "message": "Vault link deleted"}


# === CONTENT DELIVERY ENDPOINTS ===

@vault_router.get("/sign/{item_id}")
def sign_vault_item(
    item_id: int,
    expires_in: int = 3600,  # 1 hour default
    session: Session = Depends(get_session),
    validated_tenant_id: str = Depends(require_tenant_access)
):
    """Generate a signed URL for direct vault item access."""
    
    # Get vault item
    item = session.get(VaultItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Vault item not found")
    
    # Validate tenant access
    if item.tenant_id != validated_tenant_id:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: Item does not belong to specified tenant"
        )
    
    # Generate signed URL
    sign_result = vault_storage.sign_get(item.storage_key, expires_in)
    if not sign_result or not sign_result.get("signed_url"):
        raise HTTPException(status_code=500, detail="Failed to generate signed URL")
    
    return {
        "success": True,
        "signed_url": sign_result["signed_url"],
        "expires_in": expires_in,
        "item_name": item.name,
        "mime": item.mime
    }


@vault_router.get("/claim/{claim_code}")
def claim_vault_content(
    claim_code: str,
    session: Session = Depends(get_session),
    user_agent: Optional[str] = Header(None)
):
    """Claim vault content via claim link (public endpoint)."""
    
    # Find valid vault link
    link = session.exec(
        select(VaultLink).where(VaultLink.claim_code == claim_code)
    ).first()
    
    if not link:
        raise HTTPException(status_code=404, detail="Invalid claim code")
    
    # Check if link is expired
    if link.expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Claim link expired")
    
    # Check usage limits
    if link.max_uses and link.used_count >= link.max_uses:
        raise HTTPException(status_code=410, detail="Claim link usage limit exceeded")
    
    # Get vault item
    item = session.get(VaultItem, link.vault_item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Vault item not found")
    
    # Log access
    from app.models_vaults import VaultAccessChannel, VaultAccessAction
    access_log = VaultAccessLog(
        tenant_id=item.tenant_id,
        vault_link_id=link.id,
        vault_item_id=item.id,
        channel=VaultAccessChannel.web,
        action=VaultAccessAction.viewed,
        ua=user_agent,
        ts=datetime.utcnow()
    )
    session.add(access_log)
    
    # Increment use count
    link.used_count += 1
    session.commit()
    
    # Generate signed URL for immediate access
    sign_result = vault_storage.sign_get(item.storage_key, 300)  # 5 min
    if not sign_result or not sign_result.get("signed_url"):
        raise HTTPException(status_code=500, detail="Failed to generate access URL")
    
    # Redirect to signed URL
    return RedirectResponse(url=sign_result["signed_url"], status_code=302)


@vault_router.get("/deliver/{item_id}")
def deliver_vault_content(
    item_id: int,
    format: str = "url",  # url, json, telegram
    session: Session = Depends(get_session),
    validated_tenant_id: str = Depends(require_tenant_access)
):
    """Deliver vault content in different formats."""
    
    # Get vault item
    item = session.get(VaultItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Vault item not found")
    
    # Validate tenant access
    if item.tenant_id != validated_tenant_id:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: Item does not belong to specified tenant"
        )
    
    if format == "url":
        # Return signed URL
        sign_result = vault_storage.sign_get(item.storage_key, 3600)
        return {"signed_url": sign_result["signed_url"], "expires_in": 3600}
    
    elif format == "json":
        # Return metadata with content info
        return {
            "id": str(item.id),
            "name": item.name,
            "mime": item.mime,
            "size_bytes": item.size_bytes,
            "nsfw": item.nsfw,
            "created_at": item.created_at.isoformat(),
            "signed_url": vault_storage.sign_get(item.storage_key, 3600)["signed_url"]
        }
    
    elif format == "telegram":
        # Return Telegram-optimized format
        should_file = should_send_as_file(item.mime, item.nsfw)
        
        return {
            "name": item.name,
            "mime": item.mime,
            "size_bytes": item.size_bytes,
            "nsfw": item.nsfw,
            "send_as_file": should_file,
            "signed_url": vault_storage.sign_get(item.storage_key, 1800)["signed_url"],  # 30 min
            "telegram_type": "document" if should_file else "photo"
        }
    
    else:
        raise HTTPException(status_code=400, detail="Invalid format")


# === ANALYTICS AND MANAGEMENT ===

@vault_router.get("/stats")
def get_vault_stats(
    session: Session = Depends(get_session),
    validated_tenant_id: str = Depends(require_tenant_access)
):
    """Get vault storage statistics for a tenant."""
    
    # Use validated tenant ID
    tenant_id = validated_tenant_id
    
    # Get all items for tenant
    items = session.exec(
        select(VaultItem).where(VaultItem.tenant_id == tenant_id)
    ).all()
    
    # Calculate usage
    usage = calculate_storage_usage(tenant_id, list(items))
    
    # Get active links count
    active_links = session.exec(
        select(VaultLink)
        .join(VaultItem)
        .where(
            and_(
                VaultItem.id == VaultLink.vault_item_id,
                VaultItem.tenant_id == tenant_id,
                VaultLink.expires_at > datetime.utcnow()
            )
        )
    ).all()
    
    return {
        "tenant_id": tenant_id,
        "storage_usage": usage,
        "active_links": len(active_links),
        "total_items": len(items)
    }


@vault_router.get("/access-logs/{item_id}")
def get_access_logs(
    item_id: int,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_session),
    validated_tenant_id: str = Depends(require_tenant_access)
):
    """Get access logs for a vault item."""
    
    # Verify item exists
    item = session.get(VaultItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Vault item not found")
    
    # Validate tenant access
    if item.tenant_id != validated_tenant_id:
        raise HTTPException(
            status_code=403, 
            detail="Access denied: Item does not belong to specified tenant"
        )
    
    # Get access logs
    logs = session.exec(
        select(VaultAccessLog)
        .where(VaultAccessLog.vault_item_id == item_id)
        .order_by(desc(VaultAccessLog.ts))
        .offset(offset)
        .limit(limit)
    ).all()
    
    return [
        {
            "id": str(log.id),
            "vault_link_id": str(log.vault_link_id) if log.vault_link_id else None,
            "channel": log.channel.value,
            "action": log.action.value,
            "user_agent": log.ua,
            "timestamp": log.ts.isoformat()
        }
        for log in logs
    ]


# === MAINTENANCE ENDPOINTS ===

@vault_router.post("/cleanup/expired")
def cleanup_expired_links(
    session: Session = Depends(get_session),
    validated_tenant_id: str = Depends(require_tenant_access)
):
    """Clean up expired vault links for the authenticated tenant."""
    
    # Use validated tenant ID
    tenant_id = validated_tenant_id
    
    # Delete expired links for this tenant only
    expired_links = session.exec(
        select(VaultLink)
        .join(VaultItem)
        .where(
            and_(
                VaultItem.id == VaultLink.vault_item_id,
                VaultItem.tenant_id == tenant_id,
                VaultLink.expires_at < datetime.utcnow()
            )
        )
    ).all()
    
    for link in expired_links:
        session.delete(link)
    
    session.commit()
    
    return {
        "success": True,
        "cleaned_links": len(expired_links),
        "message": f"Cleaned up {len(expired_links)} expired links"
    }