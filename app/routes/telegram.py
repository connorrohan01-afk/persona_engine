"""Telegram bot endpoints."""

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from typing import Optional, Any, Dict
from app.security import verify_token
from app.config import settings

router = APIRouter(prefix="/api/v1/telegram", tags=["telegram"])


class DeployRequest(BaseModel):
    tenant_id: str = settings.tenant_default
    bot_token: str
    webhook_url: str


@router.post("/deploy")
async def telegram_deploy(
    request: DeployRequest,
    dry: Optional[bool] = Query(default=None),
    token: str = Depends(verify_token)
):
    """Deploy a Telegram bot."""
    is_dry = dry if dry is not None else settings.dry_run_default
    mode = "mock" if is_dry else "live"
    
    return {
        "ok": True,
        "mode": mode,
        "bot_username": "mock_bot" if is_dry else "real_bot",
        "webhook_url": request.webhook_url
    }


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """Handle Telegram webhook - no auth required."""
    body = await request.json()
    
    # Process webhook payload here
    # For now, just acknowledge receipt
    
    return {"ok": True}