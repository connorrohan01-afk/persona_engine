"""Vault routes for encrypted secrets and blob metadata storage."""

import json
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from cryptography.fernet import Fernet
import base64
import os
from app.security import verify_token
from app.db import get_session
from app.models import Secret, Asset
from app.config import settings
from loguru import logger


router = APIRouter(prefix="/api/v1/vault", tags=["vault"])


class SecretRequest(BaseModel):
    tenant_id: str
    key: str
    value: str


class SecretGetRequest(BaseModel):
    tenant_id: str
    key: str


class BlobRequest(BaseModel):
    tenant_id: str
    name: str
    meta: Optional[Dict[str, Any]] = None
    asset_id: str


class SecretResponse(BaseModel):
    ok: bool


class SecretGetResponse(BaseModel):
    ok: bool
    key: str
    value: str


class BlobResponse(BaseModel):
    ok: bool
    vault_blob_id: str


def get_encryption_key() -> bytes:
    """Get or generate encryption key for Fernet."""
    # Require proper encryption secret
    secret = settings.asset_signing_secret
    if not secret or len(secret) < 32:
        raise ValueError(
            "ASSET_SIGNING_SECRET environment variable must be set with at least 32 characters for secure encryption"
        )
    
    # Use PBKDF2 to derive a proper Fernet key from the secret
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    
    # Static salt for consistent key derivation (in production, consider per-tenant salts)
    salt = b"PersonaEngine_Vault_Salt_v1"
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    return key


def encrypt_value(value: str) -> str:
    """Encrypt a value using Fernet."""
    try:
        key = get_encryption_key()
        fernet = Fernet(key)
        encrypted = fernet.encrypt(value.encode())
        return base64.b64encode(encrypted).decode()
    except Exception as e:
        logger.error(f"Encryption failed: {e}")
        raise Exception("Failed to encrypt value")


def decrypt_value(encrypted_value: str) -> str:
    """Decrypt a value using Fernet."""
    try:
        key = get_encryption_key()
        fernet = Fernet(key)
        encrypted_bytes = base64.b64decode(encrypted_value.encode())
        decrypted = fernet.decrypt(encrypted_bytes)
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise Exception("Failed to decrypt value")


@router.post("/secret", response_model=SecretResponse)
async def store_secret(
    request: SecretRequest,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token)
):
    """Store an encrypted secret in the vault."""
    try:
        # Encrypt the value
        encrypted_value = encrypt_value(request.value)
        
        # Check if secret already exists
        existing_secret = session.exec(
            select(Secret).where(
                Secret.tenant_id == request.tenant_id,
                Secret.key == request.key
            )
        ).first()
        
        if existing_secret:
            # Update existing secret
            existing_secret.value_enc = encrypted_value
            existing_secret.updated_at = datetime.utcnow()
            logger.info(f"Updated secret {request.key} for tenant {request.tenant_id}")
        else:
            # Create new secret
            secret = Secret(
                tenant_id=request.tenant_id,
                key=request.key,
                value_enc=encrypted_value
            )
            session.add(secret)
            logger.info(f"Created secret {request.key} for tenant {request.tenant_id}")
        
        session.commit()
        
        return SecretResponse(ok=True)
        
    except Exception as e:
        logger.error(f"Failed to store secret {request.key}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error_code": "internal",
                "message": "Failed to store secret"
            }
        )


@router.post("/secret/get", response_model=SecretGetResponse)
async def get_secret(
    request: SecretGetRequest,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token)
):
    """Retrieve an encrypted secret from the vault."""
    try:
        # Find the secret
        secret = session.exec(
            select(Secret).where(
                Secret.tenant_id == request.tenant_id,
                Secret.key == request.key
            )
        ).first()
        
        if not secret:
            raise HTTPException(
                status_code=404,
                detail={
                    "ok": False,
                    "error_code": "not_found",
                    "message": f"Secret {request.key} not found"
                }
            )
        
        # Decrypt the value
        decrypted_value = decrypt_value(secret.value_enc)
        
        logger.info(f"Retrieved secret {request.key} for tenant {request.tenant_id}")
        
        return SecretGetResponse(
            ok=True,
            key=request.key,
            value=decrypted_value
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get secret {request.key}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error_code": "internal",
                "message": "Failed to retrieve secret"
            }
        )


@router.post("/blob", response_model=BlobResponse)
async def store_blob_metadata(
    request: BlobRequest,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token)
):
    """Store blob metadata that references an asset."""
    try:
        # Extract asset ID from ast_xxx format
        if request.asset_id.startswith("ast_"):
            asset_id = int(request.asset_id[4:])
        else:
            asset_id = int(request.asset_id)
        
        # Verify asset exists and belongs to tenant
        asset = session.get(Asset, asset_id)
        if not asset or asset.tenant_id != request.tenant_id:
            raise HTTPException(
                status_code=404,
                detail={
                    "ok": False,
                    "error_code": "asset_not_found",
                    "message": "Asset not found or access denied"
                }
            )
        
        # Create blob metadata as a JSON string stored in a secret
        blob_data = {
            "name": request.name,
            "asset_id": request.asset_id,
            "tenant_id": request.tenant_id,
            "meta": request.meta or {},
            "created_at": datetime.utcnow().isoformat(),
            "asset_url": asset.public_url,
            "asset_sha256": asset.sha256,
            "asset_mime": asset.mime
        }
        
        # Generate a unique blob key
        blob_key = f"blob_{request.name}_{asset_id}"
        
        # Store as encrypted secret
        encrypted_blob = encrypt_value(json.dumps(blob_data))
        
        # Check if blob already exists
        existing_blob = session.exec(
            select(Secret).where(
                Secret.tenant_id == request.tenant_id,
                Secret.key == blob_key
            )
        ).first()
        
        if existing_blob:
            # Update existing blob
            existing_blob.value_enc = encrypted_blob
            existing_blob.updated_at = datetime.utcnow()
            logger.info(f"Updated blob {blob_key} for tenant {request.tenant_id}")
        else:
            # Create new blob metadata
            blob_secret = Secret(
                tenant_id=request.tenant_id,
                key=blob_key,
                value_enc=encrypted_blob
            )
            session.add(blob_secret)
            logger.info(f"Created blob {blob_key} for tenant {request.tenant_id}")
        
        session.commit()
        
        # Return blob ID
        blob_id = f"vbl_{asset_id}_{hash(blob_key) % 100000}"
        
        logger.info(f"Stored blob metadata {request.name} for tenant {request.tenant_id}")
        
        return BlobResponse(
            ok=True,
            vault_blob_id=blob_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to store blob metadata {request.name}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error_code": "internal",
                "message": "Failed to store blob metadata"
            }
        )


@router.get("/blob/{blob_id}")
async def get_blob_metadata(
    blob_id: str,
    tenant_id: str,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token)
):
    """Retrieve blob metadata by ID."""
    try:
        # For this implementation, we'd need to store a mapping from blob_id to secret key
        # For simplicity, we'll return a not implemented response
        # In a full implementation, you'd maintain a separate mapping table
        
        return {
            "ok": False,
            "error_code": "not_implemented",
            "message": "Blob retrieval by ID not implemented in this version. Use secret/get with the blob key instead."
        }
        
    except Exception as e:
        logger.error(f"Failed to get blob metadata {blob_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error_code": "internal",
                "message": "Failed to retrieve blob metadata"
            }
        )


@router.get("/secrets")
async def list_secrets(
    tenant_id: str,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token)
):
    """List all secret keys for a tenant (without values)."""
    try:
        secrets = session.exec(
            select(Secret).where(Secret.tenant_id == tenant_id)
        ).all()
        
        secret_list = [
            {
                "key": secret.key,
                "created_at": secret.created_at.isoformat(),
                "updated_at": secret.updated_at.isoformat()
            }
            for secret in secrets
        ]
        
        logger.info(f"Listed {len(secret_list)} secrets for tenant {tenant_id}")
        
        return {
            "ok": True,
            "secrets": secret_list,
            "count": len(secret_list)
        }
        
    except Exception as e:
        logger.error(f"Failed to list secrets for tenant {tenant_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error_code": "internal",
                "message": "Failed to list secrets"
            }
        )