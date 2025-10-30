"""Telegram webhook integration with in-memory task queue."""

import os
import json
import time
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

# Import common Telegram utilities
from common.telegram import send_message_async

router = APIRouter(prefix="/api/v1", tags=["telegram-webhook"])

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


class TelegramMessage(BaseModel):
    """Telegram message model."""
    message_id: int
    chat: Dict[str, Any]
    text: str = ""
    from_user: Dict[str, Any] = {}


def enqueue_task(task: Dict[str, Any]) -> Dict[str, Any]:
    """Enqueue a task to the in-memory queue."""
    try:
        # Get queue from main app
        from app.main import TASK_QUEUE
        
        # Add task to queue
        TASK_QUEUE.put(task)
        
        return {
            "ok": True,
            "task_id": task.get("id"),
            "queue_position": TASK_QUEUE.qsize()
        }
    except Exception as e:
        print(f"ERROR: Failed to enqueue task: {e}")
        return {"ok": False, "error": str(e)}


async def handle_telegram_command(text: str, chat_id: str) -> Optional[str]:
    """
    Handle Telegram commands and enqueue tasks.
    
    Commands:
    - /ping - Direct reply (no queueing)
    - /build <task> - Enqueue build task
    - /status - System status
    """
    text = text.strip()
    
    # /ping - Immediate direct reply (no queueing per requirements)
    if text == "/ping":
        # Return message for immediate reply
        return "✅ Direct test pong"
    
    # /status - System status
    elif text == "/status":
        from app.main import TASK_QUEUE, worker_running
        
        status_text = f"""📊 System Status:

Worker: {'✅ Running' if worker_running else '❌ Stopped'}
Queue: {TASK_QUEUE.qsize()} tasks
Integration: Single FastAPI process (port 5000)
"""
        return status_text
    
    # /build <task> - Enqueue task
    elif text.startswith("/build"):
        # Extract task name if provided
        parts = text.split(maxsplit=1)
        task_name = parts[1] if len(parts) > 1 else "test"
        
        # Enqueue build task
        task = {
            "type": "claude.patch",
            "file_path": "test_sample.py",
            "prompt": f"Add a comment explaining the function for build task: {task_name}",
            "id": f"build_{task_name}_{int(time.time() * 1000)}"
        }
        
        result = enqueue_task(task)
        
        if result.get("ok"):
            # Return immediate reply - worker will process in background
            return f"🛠️ Queued build '{task_name}'\nTask ID: {result.get('task_id')}\nQueue position: {result.get('queue_position')}"
        else:
            return f"❌ Failed to enqueue: {result.get('error')}"
    
    # Unknown command
    else:
        return f"""❓ Available commands:

/ping - Direct test pong
/status - System status
/build <name> - Queue build task

Try: /ping"""


@router.post("/telegram/{token}")
async def telegram_webhook(token: str, request: Request):
    """
    Telegram webhook endpoint.
    
    POST /api/v1/telegram/{token}
    
    Verifies token and processes incoming messages.
    Maps commands to Manus queue and sends replies.
    """
    # Verify token
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=503, detail="Telegram bot not configured")
    
    if token != TELEGRAM_BOT_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")
    
    try:
        # Parse webhook payload
        payload = await request.json()
        
        # Extract message
        if "message" not in payload:
            return {"ok": True, "message": "No message in payload"}
        
        message = payload["message"]
        chat_id = str(message.get("chat", {}).get("id", ""))
        text = message.get("text", "")
        
        if not text:
            return {"ok": True, "message": "No text in message"}
        
        print(f"INFO: Telegram message from {chat_id}: {text}")
        
        # Handle command
        response_text = await handle_telegram_command(text, chat_id)
        
        # Only send reply if handler returned a message
        # (None means worker will handle the reply)
        if response_text is not None:
            target_chat_id = chat_id or TELEGRAM_CHAT_ID
            success = await send_message_async(target_chat_id, response_text)
            
            if success:
                print(f"INFO: Sent Telegram reply: {response_text[:50]}...")
            else:
                print(f"WARNING: Failed to send Telegram reply")
        else:
            print(f"INFO: Reply will be sent by worker")
            success = True
        
        return {
            "ok": True,
            "processed": True,
            "command": text,
            "reply_sent": success
        }
        
    except Exception as e:
        print(f"ERROR: Telegram webhook error: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")


@router.get("/telegram/info")
async def telegram_info():
    """Get Telegram webhook configuration info."""
    from app.main import TASK_QUEUE
    
    return {
        "ok": True,
        "configured": bool(TELEGRAM_BOT_TOKEN),
        "chat_id_set": bool(TELEGRAM_CHAT_ID),
        "webhook_url": f"/api/v1/telegram/<token>",
        "architecture": "Single FastAPI process with in-memory queue",
        "queue_depth": TASK_QUEUE.qsize(),
        "commands": [
            "/ping - Direct test pong (immediate)",
            "/status - System status",
            "/build <name> - Queue build task"
        ]
    }
