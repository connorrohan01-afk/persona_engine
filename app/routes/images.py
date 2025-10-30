"""Image routes for generation, ingestion, upload, and management."""

import json
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from sqlmodel import Session, select
import httpx
from app.security import verify_token
from app.db import get_session
from app.models import Asset, ImageJob, Metric
from app.storage import storage, calculate_sha256, get_file_extension, is_valid_image_mime
from app.providers.images import image_provider, check_nsfw_content
from app.config import settings
from loguru import logger


router = APIRouter(prefix="/api/v1/images", tags=["images"])


class GenerateImageRequest(BaseModel):
    tenant_id: str
    persona_id: Optional[int] = None
    prompt: str
    style: Optional[str] = None
    width: int = 768
    height: int = 1024
    nsfw: bool = False
    dry: bool = False


class IngestImageRequest(BaseModel):
    tenant_id: str
    source_url: str
    expected_mime: Optional[str] = None


class SignAssetRequest(BaseModel):
    tenant_id: str
    asset_id: str
    expires_in_seconds: int = 86400


class ImageResponse(BaseModel):
    ok: bool
    mode: str  # live, mock
    asset_id: str
    public_url: str
    sha256: str
    mime: str
    width: Optional[int] = None
    height: Optional[int] = None


class AssetMetaResponse(BaseModel):
    ok: bool
    asset: Dict[str, Any]


class SignedUrlResponse(BaseModel):
    ok: bool
    signed_url: str


def create_asset_record(
    session: Session,
    tenant_id: str,
    image_data: bytes,
    mime_type: str,
    kind: str = "image",
    meta: Optional[Dict[str, Any]] = None
) -> Asset:
    """Create an Asset record for image data."""
    # Calculate hash and path
    sha256_hash = calculate_sha256(image_data)
    ext = get_file_extension(mime_type)
    path = storage.generate_path(tenant_id, sha256_hash, ext)
    public_url = storage.get_public_url(path)
    
    # Check if asset already exists
    existing_asset = session.exec(
        select(Asset).where(
            Asset.tenant_id == tenant_id,
            Asset.sha256 == sha256_hash
        )
    ).first()
    
    if existing_asset:
        logger.info(f"Asset already exists: {existing_asset.id} (SHA256: {sha256_hash})")
        return existing_asset
    
    # Store the file
    if not storage.put_bytes(image_data, path):
        raise Exception("Failed to store image file")
    
    # Create asset record
    asset = Asset(
        tenant_id=tenant_id,
        kind=kind,
        sha256=sha256_hash,
        mime=mime_type,
        bytes=len(image_data),
        ext=ext,
        path=path,
        public_url=public_url,
        meta_json=json.dumps(meta) if meta else None
    )
    
    session.add(asset)
    session.commit()
    session.refresh(asset)
    
    logger.info(f"Created asset: {asset.id} ({len(image_data)} bytes, SHA256: {sha256_hash})")
    return asset


@router.post("/generate", response_model=ImageResponse)
async def generate_image(
    request: GenerateImageRequest,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token)
):
    """Generate an image from a text prompt."""
    try:
        # NSFW check
        if not request.nsfw and check_nsfw_content(request.prompt):
            raise HTTPException(
                status_code=400,
                detail={
                    "ok": False,
                    "error_code": "nsfw_blocked",
                    "message": "NSFW content not allowed"
                }
            )
        
        # Create ImageJob record
        image_job = ImageJob(
            tenant_id=request.tenant_id,
            persona_id=request.persona_id,
            prompt=request.prompt,
            style=request.style,
            width=request.width,
            height=request.height,
            provider=settings.img_provider,
            status="processing"
        )
        session.add(image_job)
        session.commit()
        session.refresh(image_job)
        
        # Generate image
        success, image_data, mime_type, error = image_provider.generate_image(
            prompt=request.prompt,
            style=request.style,
            width=request.width,
            height=request.height,
            dry=request.dry
        )
        
        if not success:
            # Update job with error
            image_job.status = "failed"
            image_job.error = error
            session.commit()
            
            raise HTTPException(
                status_code=400,
                detail={
                    "ok": False,
                    "error_code": "generation_failed",
                    "message": error or "Image generation failed"
                }
            )
        
        # Create asset record
        meta = {
            "prompt": request.prompt,
            "style": request.style,
            "width": request.width,
            "height": request.height,
            "provider": settings.img_provider,
            "image_job_id": image_job.id
        }
        
        asset = create_asset_record(
            session, request.tenant_id, image_data, mime_type, "image", meta
        )
        
        # Update job with success
        image_job.status = "completed"
        image_job.result_url = asset.public_url
        session.commit()
        
        # Record metric
        mode = "mock" if request.dry or image_provider.dry_run else "live"
        metric = Metric(
            tenant_id=request.tenant_id,
            persona_id=request.persona_id,
            key="image.generated",
            value_num=1.0,
            meta_json=json.dumps({
                "asset_id": asset.id,
                "provider": settings.img_provider,
                "mode": mode,
                "prompt_length": len(request.prompt)
            })
        )
        session.add(metric)
        session.commit()
        
        logger.info(f"Generated image for tenant {request.tenant_id}: {asset.id}")
        
        return ImageResponse(
            ok=True,
            mode=mode,
            asset_id=f"ast_{asset.id}",
            public_url=asset.public_url,
            sha256=asset.sha256,
            mime=asset.mime,
            width=request.width,
            height=request.height
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        
        # Update job with error if it exists
        if 'image_job' in locals():
            image_job.status = "failed"
            image_job.error = str(e)
            session.commit()
        
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error_code": "internal",
                "message": "Internal server error"
            }
        )


@router.post("/ingest", response_model=ImageResponse)
async def ingest_image(
    request: IngestImageRequest,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token)
):
    """Ingest an image from a URL."""
    try:
        # Download image
        with httpx.Client(timeout=30.0) as client:
            response = client.get(request.source_url)
            response.raise_for_status()
            
            image_data = response.content
            content_type = response.headers.get('content-type', 'application/octet-stream')
            
            # Validate content type
            if request.expected_mime and content_type != request.expected_mime:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "ok": False,
                        "error_code": "mime_mismatch",
                        "message": f"Expected {request.expected_mime}, got {content_type}"
                    }
                )
            
            # Validate image type
            if not is_valid_image_mime(content_type):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "ok": False,
                        "error_code": "invalid_mime",
                        "message": f"Invalid image MIME type: {content_type}"
                    }
                )
            
            # Check file size
            if len(image_data) > settings.max_image_mb * 1024 * 1024:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "ok": False,
                        "error_code": "file_too_large",
                        "message": f"File exceeds {settings.max_image_mb}MB limit"
                    }
                )
        
        # Create asset record
        meta = {
            "source_url": request.source_url,
            "original_content_type": content_type
        }
        
        asset = create_asset_record(
            session, request.tenant_id, image_data, content_type, "image", meta
        )
        
        # Record metric
        metric = Metric(
            tenant_id=request.tenant_id,
            key="image.ingested",
            value_num=1.0,
            meta_json=json.dumps({
                "asset_id": asset.id,
                "source_url": request.source_url,
                "file_size": len(image_data)
            })
        )
        session.add(metric)
        session.commit()
        
        logger.info(f"Ingested image for tenant {request.tenant_id}: {asset.id}")
        
        return ImageResponse(
            ok=True,
            mode="live",
            asset_id=f"ast_{asset.id}",
            public_url=asset.public_url,
            sha256=asset.sha256,
            mime=asset.mime
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image ingestion failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error_code": "internal",
                "message": "Internal server error"
            }
        )


@router.post("/upload", response_model=ImageResponse)
async def upload_image(
    file: UploadFile = File(...),
    tenant_id: str = Form(...),
    session: Session = Depends(get_session),
    token: str = Depends(verify_token)
):
    """Upload an image file."""
    try:
        # Read file data
        image_data = await file.read()
        
        # Validate file size
        if len(image_data) > settings.max_image_mb * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail={
                    "ok": False,
                    "error_code": "file_too_large",
                    "message": f"File exceeds {settings.max_image_mb}MB limit"
                }
            )
        
        # Validate content type
        content_type = file.content_type or 'application/octet-stream'
        if not is_valid_image_mime(content_type):
            raise HTTPException(
                status_code=400,
                detail={
                    "ok": False,
                    "error_code": "invalid_mime",
                    "message": f"Invalid image MIME type: {content_type}"
                }
            )
        
        # Create asset record
        meta = {
            "original_filename": file.filename,
            "upload_content_type": content_type
        }
        
        asset = create_asset_record(
            session, tenant_id, image_data, content_type, "image", meta
        )
        
        # Record metric
        metric = Metric(
            tenant_id=tenant_id,
            key="image.uploaded",
            value_num=1.0,
            meta_json=json.dumps({
                "asset_id": asset.id,
                "filename": file.filename,
                "file_size": len(image_data)
            })
        )
        session.add(metric)
        session.commit()
        
        logger.info(f"Uploaded image for tenant {tenant_id}: {asset.id}")
        
        return ImageResponse(
            ok=True,
            mode="live",
            asset_id=f"ast_{asset.id}",
            public_url=asset.public_url,
            sha256=asset.sha256,
            mime=asset.mime
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Image upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error_code": "internal",
                "message": "Internal server error"
            }
        )


@router.get("/asset", response_model=AssetMetaResponse)
async def get_asset_meta(
    id: str,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token)
):
    """Get asset metadata by ID."""
    try:
        # Extract numeric ID from ast_xxx format
        if id.startswith("ast_"):
            asset_id = int(id[4:])
        else:
            asset_id = int(id)
        
        asset = session.get(Asset, asset_id)
        if not asset:
            raise HTTPException(
                status_code=404,
                detail={
                    "ok": False,
                    "error_code": "not_found",
                    "message": "Asset not found"
                }
            )
        
        asset_data = {
            "id": f"ast_{asset.id}",
            "tenant_id": asset.tenant_id,
            "kind": asset.kind,
            "sha256": asset.sha256,
            "mime": asset.mime,
            "bytes": asset.bytes,
            "ext": asset.ext,
            "path": asset.path,
            "public_url": asset.public_url,
            "created_at": asset.created_at.isoformat(),
            "meta": json.loads(asset.meta_json) if asset.meta_json else None
        }
        
        return AssetMetaResponse(
            ok=True,
            asset=asset_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get asset meta: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error_code": "internal",
                "message": "Internal server error"
            }
        )


@router.post("/sign", response_model=SignedUrlResponse)
async def sign_asset_url(
    request: SignAssetRequest,
    session: Session = Depends(get_session),
    token: str = Depends(verify_token)
):
    """Generate a signed URL for an asset."""
    try:
        # Extract numeric ID from ast_xxx format
        if request.asset_id.startswith("ast_"):
            asset_id = int(request.asset_id[4:])
        else:
            asset_id = int(request.asset_id)
        
        asset = session.get(Asset, asset_id)
        if not asset:
            raise HTTPException(
                status_code=404,
                detail={
                    "ok": False,
                    "error_code": "not_found", 
                    "message": "Asset not found"
                }
            )
        
        if asset.tenant_id != request.tenant_id:
            raise HTTPException(
                status_code=403,
                detail={
                    "ok": False,
                    "error_code": "forbidden",
                    "message": "Access denied - asset belongs to different tenant"
                }
            )
        
        # Import signing function from assets router
        from app.routes.assets import sign_url
        import time
        
        # Generate signed URL
        expires_at = int(time.time()) + request.expires_in_seconds
        signature = sign_url(asset.path, expires_at)
        signed_url = f"{settings.public_base_url}{asset.path}?exp={expires_at}&sig={signature}"
        
        logger.info(f"Generated signed URL for asset {asset.id} (tenant: {request.tenant_id})")
        
        return SignedUrlResponse(
            ok=True,
            signed_url=signed_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to sign asset URL: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error_code": "internal",
                "message": "Internal server error"
            }
        )