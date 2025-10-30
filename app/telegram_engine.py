"""Telegram engine for PersonaEngine persona deployer."""

import asyncio
import httpx
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from loguru import logger

from app.config import settings


class TelegramEngine:
    """Telegram message sending and webhook processing engine."""
    
    def __init__(self):
        self.timeout = 30
        self.max_retries = 3
        
    async def send_message(
        self,
        bot_token: str,
        chat_id: str,
        text: str,
        parse_mode: Optional[str] = None,
        disable_web_page_preview: bool = False,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Send a message via Telegram Bot API."""
        
        if dry_run:
            logger.info(f"[DRY RUN] Would send Telegram message to chat_id={chat_id}: {text[:100]}...")
            return {
                "ok": True,
                "result": {
                    "message_id": 999999,
                    "date": int(datetime.utcnow().timestamp()),
                    "chat": {"id": int(chat_id), "type": "private"},
                    "text": text
                },
                "dry_run": True
            }
        
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": disable_web_page_preview
        }
        
        if parse_mode:
            payload["parse_mode"] = parse_mode
            
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Telegram message sent successfully to chat_id={chat_id}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Telegram API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Telegram API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {str(e)}")
            raise Exception(f"Failed to send message: {str(e)}")
    
    def parse_update(self, update_json: Union[Dict, str]) -> Dict[str, Any]:
        """Parse Telegram webhook update and extract key information."""
        
        if isinstance(update_json, str):
            try:
                update = json.loads(update_json)
            except json.JSONDecodeError:
                logger.error("Invalid JSON in Telegram update")
                return {"chat_id": None, "text": None, "error": "Invalid JSON"}
        else:
            update = update_json
            
        try:
            # Extract message info
            message = update.get("message", {})
            chat = message.get("chat", {})
            chat_id = str(chat.get("id", ""))
            text = message.get("text", "")
            
            # Extract additional useful info
            user = message.get("from", {})
            user_id = user.get("id")
            username = user.get("username")
            first_name = user.get("first_name", "")
            
            return {
                "chat_id": chat_id,
                "text": text,
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "message_id": message.get("message_id"),
                "date": message.get("date"),
                "update_id": update.get("update_id")
            }
            
        except Exception as e:
            logger.error(f"Failed to parse Telegram update: {str(e)}")
            return {"chat_id": None, "text": None, "error": str(e)}
    
    async def route_message(
        self,
        update_json: Dict[str, Any],
        persona_config: Dict[str, Any],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Route incoming message and handle upsell triggers."""
        
        parsed = self.parse_update(update_json)
        chat_id = parsed.get("chat_id")
        text = parsed.get("text", "").lower()
        
        if not chat_id or not text:
            return {"handled": False, "error": "No chat_id or text found"}
        
        # Check for upsell triggers
        upsell_text = persona_config.get("upsell_text", settings.telegram_default_upsell)
        upsell_triggers = persona_config.get("upsell_triggers", ["vault", "link", "upsell"])
        
        # Check if message contains any upsell triggers
        triggered = any(trigger.lower() in text for trigger in upsell_triggers)
        
        if triggered:
            logger.info(f"Upsell triggered for chat_id={chat_id}, sending: {upsell_text}")
            
            try:
                # Send upsell message
                bot_token = persona_config.get("bot_token")
                if not bot_token:
                    return {"handled": False, "error": "No bot token configured"}
                
                result = await self.send_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    text=upsell_text,
                    dry_run=dry_run
                )
                
                return {
                    "handled": True,
                    "triggered": True,
                    "upsell_sent": True,
                    "message_result": result,
                    "trigger_text": text,
                    "response_text": upsell_text
                }
                
            except Exception as e:
                logger.error(f"Failed to send upsell message: {str(e)}")
                return {
                    "handled": True,
                    "triggered": True,
                    "upsell_sent": False,
                    "error": str(e)
                }
        else:
            # Message received but no trigger - just log it
            logger.info(f"Message received from chat_id={chat_id}: {text[:100]}...")
            return {
                "handled": True,
                "triggered": False,
                "upsell_sent": False,
                "message_text": text
            }
    
    async def set_webhook(
        self,
        bot_token: str,
        webhook_url: str,
        secret_token: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Set webhook URL for a Telegram bot with secret token for security."""
        
        if dry_run:
            logger.info(f"[DRY RUN] Would set webhook for bot to: {webhook_url}")
            return {"ok": True, "description": "Webhook was set (dry run)", "dry_run": True}
        
        url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        payload = {"url": webhook_url}
        
        # Add secret token for webhook security
        if secret_token:
            payload["secret_token"] = secret_token
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Webhook set successfully: {webhook_url}")
                return result
                
        except Exception as e:
            logger.error(f"Failed to set webhook: {str(e)}")
            raise Exception(f"Failed to set webhook: {str(e)}")
    
    async def get_bot_info(
        self,
        bot_token: str,
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """Get information about the bot."""
        
        if dry_run:
            logger.info(f"[DRY RUN] Would get bot info")
            return {
                "ok": True,
                "result": {
                    "id": 123456789,
                    "is_bot": True,
                    "first_name": "Test Bot",
                    "username": "testbot",
                    "can_join_groups": True,
                    "can_read_all_group_messages": False,
                    "supports_inline_queries": False
                },
                "dry_run": True
            }
        
        url = f"https://api.telegram.org/bot{bot_token}/getMe"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Bot info retrieved successfully")
                return result
                
        except Exception as e:
            logger.error(f"Failed to get bot info: {str(e)}")
            raise Exception(f"Failed to get bot info: {str(e)}")


# Global telegram engine instance
telegram_engine = TelegramEngine()