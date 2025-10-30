"""Link shortening and tracking endpoints."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from typing import Optional
from app.security import verify_token
from app.config import settings

router = APIRouter(prefix="/api/v1/link", tags=["links"])


class ShortenRequest(BaseModel):
    tenant_id: str = settings.tenant_default
    url: str
    custom_slug: Optional[str] = None


@router.post("/shorten")
async def shorten_link(
    request: ShortenRequest,
    dry: Optional[bool] = Query(default=None),
    token: str = Depends(verify_token)
):
    """Shorten a URL."""
    is_dry = dry if dry is not None else settings.dry_run_default
    mode = "mock" if is_dry else "live"
    
    link_id = request.custom_slug or "abc123"
    
    return {
        "ok": True,
        "mode": mode,
        "link_id": link_id,
        "short_url": f"https://short.ly/{link_id}" if is_dry else f"https://real-short.ly/{link_id}"
    }


@router.post("/click")
async def link_click(
    link_id: str,
    tenant_id: str = settings.tenant_default,
    persona_id: Optional[int] = None,
    account_id: Optional[int] = None,
    ref: Optional[str] = None
):
    """Track a link click - no auth required for public links."""
    
    return {
        "ok": True,
        "redirect_url": "https://example.com/original-url",
        "tracked": True
    }