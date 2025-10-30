"""Telegram Persona API routes for PersonaEngine."""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import settings
from app.db import engine
from app.models_telegram_persona import TelegramPersona
from app.telegram_engine import telegram_engine
from app.security import verify_token

router = APIRouter(prefix="/api/v1/telegram/persona", tags=["telegram-persona"])


# Request/Response Models
class DeployRequest(BaseModel):
    tenant_id: str = "owner"
    persona_id: str
    bot_token: str
    username: str
    enabled: bool = True
    dry: bool = False


class LinkRequest(BaseModel):
    telegram_persona_id: str
    persona_id: str


class SendTestRequest(BaseModel):
    telegram_persona_id: str
    chat_id: str
    text: str


class ToggleRequest(BaseModel):
    telegram_persona_id: str
    enabled: bool


# Helper functions
def get_telegram_persona_by_id(db: Session, telegram_persona_id: str) -> TelegramPersona:
    """Get telegram persona by formatted ID (e.g., 'tp_001')."""
    if not telegram_persona_id.startswith("tp_"):
        raise HTTPException(status_code=400, detail="Invalid telegram_persona_id format")
    
    try:
        # Extract numeric ID from tp_XXX format
        numeric_id = int(telegram_persona_id[3:])
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid telegram_persona_id format")
    
    persona = db.exec(
        select(TelegramPersona).where(TelegramPersona.id == numeric_id)
    ).first()
    
    if not persona:
        raise HTTPException(status_code=404, detail="Telegram persona not found")
    
    return persona


# Route implementations
@router.post("/deploy")
async def deploy_persona(
    request: DeployRequest,
    token: str = Depends(verify_token)
):
    """Deploy a new Telegram persona bot."""
    # Force dry mode if DRY_DEFAULT is set
    dry = request.dry or bool(settings.dry_default)
    mode = "dry" if dry else "live"
    
    try:
        # Validate bot token by getting bot info
        if not dry:
            bot_info = await telegram_engine.get_bot_info(request.bot_token, dry_run=dry)
            if not bot_info.get("ok"):
                raise HTTPException(status_code=400, detail="Invalid bot token")
        
        with Session(engine) as db:
            # Check if bot already exists
            existing = db.exec(
                select(TelegramPersona)
                .where(TelegramPersona.bot_token == request.bot_token)
            ).first()
            
            if existing:
                raise HTTPException(status_code=400, detail="Bot token already deployed")
            
            # Create new telegram persona
            persona = TelegramPersona(
                tenant_id=request.tenant_id,
                persona_id=request.persona_id,
                bot_token=request.bot_token,
                username=request.username,
                linked=True,  # Auto-link on deploy
                enabled=request.enabled,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.add(persona)
            db.commit()
            db.refresh(persona)
            
            # Generate webhook URL
            webhook_url = persona.get_webhook_url(settings.telegram_webhook_base)
            
            # Set webhook with secret token if not dry run
            if not dry:
                try:
                    # Use the cryptographically secure secret stored in the persona
                    await telegram_engine.set_webhook(
                        bot_token=request.bot_token,
                        webhook_url=webhook_url,
                        secret_token=persona.webhook_secret,
                        dry_run=dry
                    )
                except Exception as e:
                    # Rollback persona creation if webhook fails
                    db.delete(persona)
                    db.commit()
                    raise HTTPException(status_code=500, detail=f"Failed to set webhook: {str(e)}")
            
            return {
                "ok": True,
                "mode": mode,
                "telegram_persona_id": persona.get_telegram_persona_id(),
                "webhook_url": webhook_url,
                "bot_username": request.username,
                "linked": True,
                "enabled": request.enabled
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")


@router.post("/link")
async def link_persona(
    request: LinkRequest,
    token: str = Depends(verify_token)
):
    """Link a Telegram persona to a persona in the registry."""
    try:
        with Session(engine) as db:
            persona = get_telegram_persona_by_id(db, request.telegram_persona_id)
            
            # Update persona_id and linked status
            persona.persona_id = request.persona_id
            persona.linked = True
            persona.updated_at = datetime.utcnow()
            
            db.add(persona)
            db.commit()
            
            return {
                "ok": True,
                "linked": True,
                "telegram_persona_id": request.telegram_persona_id,
                "persona_id": request.persona_id
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Link failed: {str(e)}")


@router.post("/send-test")
async def send_test_message(
    request: SendTestRequest,
    token: str = Depends(verify_token)
):
    """Send a test message from a Telegram persona bot."""
    # Force dry mode if DRY_DEFAULT is set
    dry = bool(settings.dry_default)
    mode = "dry" if dry else "live"
    
    try:
        with Session(engine) as db:
            persona = get_telegram_persona_by_id(db, request.telegram_persona_id)
            
            if not persona.enabled:
                raise HTTPException(status_code=400, detail="Telegram persona is disabled")
            
            # Send test message
            result = await telegram_engine.send_message(
                bot_token=persona.bot_token,
                chat_id=request.chat_id,
                text=request.text,
                dry_run=dry
            )
            
            return {
                "ok": True,
                "mode": mode,
                "sent": result.get("ok", False),
                "message_id": result.get("result", {}).get("message_id"),
                "chat_id": request.chat_id,
                "text": request.text,
                "dry_run": dry
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Send test failed: {str(e)}")


@router.post("/toggle")
async def toggle_persona(
    request: ToggleRequest,
    token: str = Depends(verify_token)
):
    """Toggle enabled/disabled status of a Telegram persona."""
    # Force dry mode if DRY_DEFAULT is set
    dry = bool(settings.dry_default)
    mode = "dry" if dry else "live"
    
    try:
        with Session(engine) as db:
            persona = get_telegram_persona_by_id(db, request.telegram_persona_id)
            
            # Update enabled status
            persona.enabled = request.enabled
            persona.updated_at = datetime.utcnow()
            
            db.add(persona)
            db.commit()
            
            return {
                "ok": True,
                "mode": mode,
                "telegram_persona_id": request.telegram_persona_id,
                "enabled": request.enabled,
                "updated_at": persona.updated_at.isoformat()
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Toggle failed: {str(e)}")


@router.get("/status")
async def get_persona_status(
    id: str = Query(..., description="Telegram persona ID (e.g., tp_001)"),
    token: str = Depends(verify_token)
):
    """Get status of a Telegram persona."""
    try:
        with Session(engine) as db:
            persona = get_telegram_persona_by_id(db, id)
            
            return {
                "ok": True,
                "persona": {
                    "id": persona.get_telegram_persona_id(),
                    "tenant_id": persona.tenant_id,
                    "persona_id": persona.persona_id,
                    "username": persona.username,
                    "linked": persona.linked,
                    "enabled": persona.enabled,
                    "created_at": persona.created_at.isoformat(),
                    "updated_at": persona.updated_at.isoformat()
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


@router.post("/webhook/{telegram_persona_id}")
async def webhook_handler(
    telegram_persona_id: str,
    request: Request
):
    """Handle Telegram webhook updates for a specific persona."""
    try:
        # Get the raw JSON body
        update_json = await request.json()
        
        with Session(engine) as db:
            persona = get_telegram_persona_by_id(db, telegram_persona_id)
            
            # Validate webhook secret token for security using stored secret
            secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            
            if not secret_token or secret_token != persona.webhook_secret:
                from loguru import logger
                logger.warning(f"Invalid webhook secret token for {telegram_persona_id}")
                raise HTTPException(status_code=403, detail="Invalid secret token")
            
            if not persona.enabled:
                return {"ok": False, "error": "Persona disabled"}
            
            # Prepare persona config for routing
            persona_config = {
                "bot_token": persona.bot_token,
                "upsell_text": settings.telegram_default_upsell,
                "upsell_triggers": ["vault", "link", "upsell", "check out"]
            }
            
            # Force dry mode if DRY_DEFAULT is set
            dry = bool(settings.dry_default)
            
            # Route the message
            result = await telegram_engine.route_message(
                update_json=update_json,
                persona_config=persona_config,
                dry_run=dry
            )
            
            return {
                "ok": True,
                "telegram_persona_id": telegram_persona_id,
                "handled": result.get("handled", False),
                "triggered": result.get("triggered", False),
                "upsell_sent": result.get("upsell_sent", False),
                "mode": "dry" if dry else "live"
            }
            
    except HTTPException:
        raise
    except Exception as e:
        # Don't raise HTTP errors for webhook - just log and return ok
        from loguru import logger
        logger.error(f"Webhook error for {telegram_persona_id}: {str(e)}")
        return {"ok": False, "error": str(e)}