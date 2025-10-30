"""Common Telegram utilities for sending messages."""

import os
import httpx
from typing import Optional


def send_message(chat_id: str, text: str, parse_mode: str = "Markdown") -> bool:
    """
    Send a message to a Telegram chat.
    
    Args:
        chat_id: The chat ID to send the message to
        text: The message text to send
        parse_mode: Parse mode for formatting (default: "Markdown")
    
    Returns:
        True if message was sent successfully, False otherwise
    
    Environment Variables:
        TELEGRAM_BOT_TOKEN: The bot token for authentication
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    if not bot_token:
        print("WARNING: TELEGRAM_BOT_TOKEN not configured")
        return False
    
    if not chat_id:
        print("WARNING: No chat ID provided")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    try:
        response = httpx.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode
            },
            timeout=10.0
        )
        
        if response.status_code == 200:
            return True
        else:
            print(f"ERROR: Telegram API returned {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"ERROR: Failed to send Telegram message: {e}")
        return False


async def send_message_async(chat_id: str, text: str, parse_mode: str = "Markdown") -> bool:
    """
    Send a message to a Telegram chat (async version).
    
    Args:
        chat_id: The chat ID to send the message to
        text: The message text to send
        parse_mode: Parse mode for formatting (default: "Markdown")
    
    Returns:
        True if message was sent successfully, False otherwise
    
    Environment Variables:
        TELEGRAM_BOT_TOKEN: The bot token for authentication
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    
    if not bot_token:
        print("WARNING: TELEGRAM_BOT_TOKEN not configured")
        return False
    
    if not chat_id:
        print("WARNING: No chat ID provided")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode
                },
                timeout=10.0
            )
            
            if response.status_code == 200:
                return True
            else:
                print(f"ERROR: Telegram API returned {response.status_code}: {response.text}")
                return False
                
    except Exception as e:
        print(f"ERROR: Failed to send Telegram message: {e}")
        return False
