import os
import requests
import logging
from typing import Union

logger = logging.getLogger(__name__)

def get_token() -> str:
    """Get Telegram bot token from environment variable"""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN environment variable is required. "
            "Get your bot token from @BotFather on Telegram and set it in your environment."
        )
    return token

def send_message(chat_id: Union[int, str], text: str) -> dict:
    """Send a message to a Telegram chat"""
    try:
        token = get_token()
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        
        payload = {
            "chat_id": chat_id,
            "text": text
        }
        
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        
        if response.status_code == 200:
            logger.info(f"Message sent to chat {chat_id}: {text[:50]}...")
            return result
        else:
            logger.error(f"Failed to send message to chat {chat_id}: {result.get('description', 'Unknown error')}")
            return {"ok": False, "error": result.get("description", "Unknown error")}
    
    except ValueError as e:
        # Token not set
        logger.error(f"Token error: {str(e)}")
        return {"ok": False, "error": str(e)}
    except requests.RequestException as e:
        logger.error(f"Request failed for chat {chat_id}: {str(e)}")
        return {"ok": False, "error": f"Request failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error sending message to chat {chat_id}: {str(e)}")
        return {"ok": False, "error": f"Unexpected error: {str(e)}"}

def send_photo(chat_id: Union[int, str], photo_url: str, caption: str = None) -> bool:
    """Send a photo to a Telegram chat via URL"""
    try:
        token = get_token()
        url = f"https://api.telegram.org/bot{token}/sendPhoto"
        
        payload = {
            "chat_id": chat_id,
            "photo": photo_url
        }
        
        if caption:
            payload["caption"] = caption
        
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        
        if response.status_code == 200:
            logger.info(f"Photo sent to chat {chat_id}: {photo_url}")
            return True
        else:
            logger.error(f"Failed to send photo to chat {chat_id}: {result.get('description', 'Unknown error')}")
            return False
    
    except ValueError as e:
        logger.error(f"Token error: {str(e)}")
        return False
    except requests.RequestException as e:
        logger.error(f"Request failed for chat {chat_id}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending photo to chat {chat_id}: {str(e)}")
        return False

def safe_send(chat_id: Union[int, str], text: str) -> bool:
    """Safely send a message, logs errors but never crashes the webhook"""
    try:
        result = send_message(chat_id, text)
        return result.get("ok", False)
    except Exception as e:
        logger.error(f"safe_send failed for chat {chat_id}: {str(e)}")
        return False

def set_webhook(base_url: str) -> dict:
    """Set the webhook URL for the Telegram bot"""
    try:
        token = get_token()
        webhook_url = f"{base_url}/api/v1/hooks/telegram"
        url = f"https://api.telegram.org/bot{token}/setWebhook"
        
        payload = {
            "url": webhook_url
        }
        
        response = requests.post(url, json=payload, timeout=10)
        result = response.json()
        
        if response.status_code == 200:
            logger.info(f"Webhook set to: {webhook_url}")
            return result
        else:
            logger.error(f"Failed to set webhook: {result.get('description', 'Unknown error')}")
            return {"ok": False, "error": result.get("description", "Unknown error")}
    
    except ValueError as e:
        logger.error(f"Token error: {str(e)}")
        return {"ok": False, "error": str(e)}
    except requests.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        return {"ok": False, "error": f"Request failed: {str(e)}"}
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {"ok": False, "error": f"Unexpected error: {str(e)}"}