"""Asset routes for signed URL generation and validation."""

import hmac
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlmodel import Session, select
from app.security import verify_token
from app.db import get_session
from app.models import Asset
from app.storage import storage
from app.config import settings
from loguru import logger
import io


# Asset serving router with both API routes and public CDN routes
api_router = APIRouter(prefix="/api/v1/assets", tags=["assets"])
cdn_router = APIRouter(tags=["assets"])


class SignUrlRequest(BaseModel):
    tenant_id: str
    path: str
    expires_in_seconds: int = 3600


class SignUrlResponse(BaseModel):
    ok: bool
    signed_url: str


def get_signing_secret() -> str:
    """Get the signing secret for URLs."""
    secret = settings.asset_signing_secret
    if not secret or len(secret) < 32:
        raise ValueError(
            "ASSET_SIGNING_SECRET environment variable must be set with at least 32 characters for secure URL signing"
        )
    
    return secret


def sign_url(path: str, expires_at: int) -> str:
    """Generate HMAC signature for URL."""
    secret = get_signing_secret()
    message = f"{path}:{expires_at}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return signature


def verify_signature(path: str, expires_at: int, signature: str) -> bool:
    """Verify HMAC signature for URL."""
    expected_signature = sign_url(path, expires_at)
    return hmac.compare_digest(expected_signature, signature)


@api_router.post("/sign", response_model=SignUrlResponse)
async def sign_asset_url(
    request: SignUrlRequest,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token)
):
    """
    Generate a signed URL for an asset path.
    """
    try:
        # Validate path format and tenant ownership
        if not request.path.startswith(f"/cdn/{request.tenant_id}/"):
            raise HTTPException(
                status_code=403,
                detail={
                    "ok": False,
                    "error_code": "forbidden",
                    "message": "Path must belong to the specified tenant"
                }
            )
        
        # Verify asset exists and belongs to tenant
        asset = session.exec(
            select(Asset).where(
                Asset.tenant_id == request.tenant_id,
                Asset.path == request.path
            )
        ).first()
        
        if not asset:
            raise HTTPException(
                status_code=404,
                detail={
                    "ok": False,
                    "error_code": "not_found",
                    "message": "Asset not found or access denied"
                }
            )
        
        # Calculate expiration timestamp
        expires_at = int(time.time()) + request.expires_in_seconds
        
        # Generate signature
        signature = sign_url(request.path, expires_at)
        
        # Build signed URL
        base_url = settings.public_base_url
        signed_url = f"{base_url}{request.path}?exp={expires_at}&sig={signature}"
        
        logger.info(f"Generated signed URL for {request.path} (tenant: {request.tenant_id})")
        
        return SignUrlResponse(
            ok=True,
            signed_url=signed_url
        )
        
    except Exception as e:
        logger.error(f"Failed to sign URL {request.path}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error_code": "internal",
                "message": "Failed to generate signed URL"
            }
        )


@cdn_router.get("/cdn/{tenant_id}/{year:int}/{month:str}/{filename}")
async def serve_asset(
    tenant_id: str,
    year: int,
    month: str,
    filename: str,
    exp: Optional[int] = Query(None, description="Expiration timestamp"),
    sig: Optional[str] = Query(None, description="HMAC signature"),
    session: Session = Depends(get_session)
):
    """
    Serve a signed asset file.
    """
    try:
        # Reconstruct the path
        path = f"/cdn/{tenant_id}/{year}/{month}/{filename}"
        
        # Require valid signature for access
        if exp is None or sig is None:
            raise HTTPException(
                status_code=401,
                detail={
                    "ok": False,
                    "error_code": "unauthorized",
                    "message": "Signed URL required (missing exp or sig parameters)"
                }
            )
        
        # Validate signature
        if exp is not None and sig is not None:
            # Check expiration
            current_time = int(time.time())
            if current_time > exp:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "ok": False,
                        "error_code": "expired",
                        "message": "Signed URL has expired"
                    }
                )
            
            # Verify signature
            if not verify_signature(path, exp, sig):
                raise HTTPException(
                    status_code=403,
                    detail={
                        "ok": False,
                        "error_code": "invalid_signature",
                        "message": "Invalid signature"
                    }
                )
        
        # Check if asset exists in database
        asset = session.exec(
            select(Asset).where(
                Asset.tenant_id == tenant_id,
                Asset.path == path
            )
        ).first()
        
        if not asset:
            raise HTTPException(
                status_code=404,
                detail={
                    "ok": False,
                    "error_code": "not_found",
                    "message": "Asset not found"
                }
            )
        
        # Check if file exists in storage
        if not storage.exists(path):
            logger.error(f"Asset record exists but file missing: {path}")
            raise HTTPException(
                status_code=404,
                detail={
                    "ok": False,
                    "error_code": "file_missing",
                    "message": "Asset file not found in storage"
                }
            )
        
        # Get file data
        file_data = storage.get_bytes(path)
        if not file_data:
            raise HTTPException(
                status_code=500,
                detail={
                    "ok": False,
                    "error_code": "read_error",
                    "message": "Failed to read asset file"
                }
            )
        
        # Create streaming response
        def iterfile():
            yield file_data
        
        headers = {
            "Content-Length": str(len(file_data)),
            "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
            "ETag": f'"{asset.sha256}"'
        }
        
        return StreamingResponse(
            io.BytesIO(file_data),
            media_type=asset.mime,
            headers=headers
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to serve asset {path}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error_code": "internal",
                "message": "Failed to serve asset"
            }
        )


@api_router.get("/verify")
async def verify_signed_url(
    path: str = Query(..., description="Asset path"),
    exp: int = Query(..., description="Expiration timestamp"),
    sig: str = Query(..., description="HMAC signature")
):
    """
    Verify a signed URL without serving the asset.
    """
    try:
        # Check expiration
        current_time = int(time.time())
        if current_time > exp:
            return {
                "ok": False,
                "error_code": "expired",
                "message": "Signed URL has expired"
            }
        
        # Verify signature
        if not verify_signature(path, exp, sig):
            return {
                "ok": False,
                "error_code": "invalid_signature",
                "message": "Invalid signature"
            }
        
        return {
            "ok": True,
            "valid": True,
            "expires_at": datetime.fromtimestamp(exp).isoformat(),
            "expires_in_seconds": max(0, exp - current_time)
        }
        
    except Exception as e:
        logger.error(f"Failed to verify signed URL: {e}")
        return {
            "ok": False,
            "error_code": "internal",
            "message": "Failed to verify URL"
        }