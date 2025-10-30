"""
Single-process FastAPI app with Telegram webhook integration.
Minimal and deterministic file operations via Claude AI.
"""

import os
import time
import httpx
from queue import Queue
from threading import Thread
from typing import Dict, Any
from fastapi import FastAPI, Request

# Import SDK runner
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from sdk.runner import patch_file
from utils.files import read_text, sha1

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID_DEFAULT = os.getenv("TELEGRAM_CHAT_ID", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# In-memory task queue
TASK_QUEUE: Queue = Queue()

# FastAPI app
app = FastAPI()

# Pending patch context (chat_id -> path mapping)
PENDING_PATCHES: Dict[str, str] = {}


def send_telegram_message(chat_id: str, text: str) -> bool:
    """
    Send a message to Telegram.
    
    Args:
        chat_id: Chat ID to send to
        text: Message text
        
    Returns:
        True if successful, False otherwise
    """
    if not TELEGRAM_BOT_TOKEN:
        print(f"ERROR: TELEGRAM_BOT_TOKEN not configured")
        return False
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    try:
        response = httpx.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text
            },
            timeout=10.0
        )
        
        if response.status_code == 200:
            print(f"✅ Sent Telegram message to {chat_id}")
            return True
        else:
            print(f"❌ Telegram API error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")
        return False


def worker():
    """
    Background worker thread that processes tasks from the queue.
    """
    print("✅ Worker thread started")
    
    while True:
        try:
            task = TASK_QUEUE.get(timeout=1.0)
            
            task_type = task.get("type")
            print(f"📋 Processing task: {task_type}")
            
            if task_type == "patch":
                # Process patch task
                path = task.get("path", "")
                goal = task.get("goal", "")
                chat_id = task.get("chat_id", "")
                
                if not path or not goal:
                    print(f"❌ Invalid patch task: missing path or goal")
                    TASK_QUEUE.task_done()
                    continue
                
                # Call SDK runner
                result = patch_file(path, goal)
                
                if result.get("ok"):
                    # Success: send confirmation to Telegram
                    lines_changed = result.get("lines_changed", 0)
                    sha1_after = result.get("sha1_after", "UNKNOWN")
                    
                    message = f"""✅ Patch Applied
File: {path}
Lines changed: {lines_changed}
SHA1: {sha1_after}"""
                    
                    send_telegram_message(chat_id, message)
                    print(f"✅ Patch applied successfully: {path}")
                else:
                    # Error: send error message
                    error = result.get("error", "Unknown error")
                    message = f"""❌ Patch Failed
File: {path}
Error: {error}"""
                    
                    send_telegram_message(chat_id, message)
                    print(f"❌ Patch failed: {error}")
            
            TASK_QUEUE.task_done()
            
        except Exception as e:
            # Timeout or other error - continue loop
            pass


# Start worker thread on app startup
@app.on_event("startup")
async def startup():
    """Start background worker thread."""
    worker_thread = Thread(target=worker, daemon=True)
    worker_thread.start()
    
    print("\n" + "=" * 60)
    print("🚀 Telegram File Bot - Single Process")
    print("=" * 60)
    print(f"✅ Worker running")
    print(f"✅ Routes:")
    print(f"   - GET  /api/v1/health")
    print(f"   - POST /api/v1/telegram/{{token}}")
    print(f"✅ Webhook URL: /api/v1/telegram/{TELEGRAM_BOT_TOKEN[:20]}...")
    print("=" * 60 + "\n")


@app.get("/")
async def root():
    """
    Root endpoint for platform probes.
    
    Returns:
        Dict with ok status
    """
    return {"ok": True}


@app.get("/api/v1/health")
async def health():
    """
    Health check endpoint.
    
    Returns:
        Dict with ok status and queue depth
    """
    return {
        "ok": True,
        "queue_depth": TASK_QUEUE.qsize()
    }


@app.post("/api/v1/telegram/{token}")
async def telegram_webhook(token: str, request: Request):
    """
    Telegram webhook endpoint.
    
    Args:
        token: Bot token (must match env variable)
        request: FastAPI request object
        
    Returns:
        Dict with ok status
    """
    # Validate token
    if token != TELEGRAM_BOT_TOKEN:
        print(f"⚠️  Invalid token received")
        return {"ok": True}  # Return 200 anyway to avoid Telegram retry
    
    # Parse update
    update = await request.json()
    
    # Extract message
    msg = update.get("message", {})
    text = (msg.get("text") or "").strip()
    chat_id = str(msg.get("chat", {}).get("id") or CHAT_ID_DEFAULT)
    
    if not text:
        return {"ok": True}
    
    print(f"📥 Telegram message from {chat_id}: {text[:50]}")
    
    # Check if this is a pending patch goal
    if chat_id in PENDING_PATCHES:
        # This message is the goal for a pending patch
        path = PENDING_PATCHES[chat_id]
        goal = text
        
        # Remove from pending
        del PENDING_PATCHES[chat_id]
        
        # Enqueue patch task
        TASK_QUEUE.put({
            "type": "patch",
            "path": path,
            "goal": goal,
            "chat_id": chat_id
        })
        
        send_telegram_message(chat_id, f"🛠️ Queued build: {path}")
        print(f"✅ Enqueued patch task for {path}")
        
        return {"ok": True}
    
    # Handle commands
    if text == "/ping":
        send_telegram_message(chat_id, "✅ Direct test pong")
        print(f"✅ Handled /ping")
        
    elif text == "/status":
        queue_depth = TASK_QUEUE.qsize()
        send_telegram_message(chat_id, f"📊 System OK | Queue: {queue_depth}")
        print(f"✅ Handled /status")
        
    elif text.startswith("/build read "):
        # Extract path
        path = text[12:].strip()
        
        try:
            # Read file
            content = read_text(path)
            file_hash = sha1(path)
            
            # Truncate to first 1200 chars
            preview = content[:1200]
            if len(content) > 1200:
                preview += "\n... (truncated)"
            
            message = f"""📄 File: {path}
SHA1: {file_hash}

Content:
{preview}"""
            
            send_telegram_message(chat_id, message)
            print(f"✅ Read file: {path}")
            
        except FileNotFoundError:
            send_telegram_message(chat_id, f"❌ File not found: {path}")
            print(f"❌ File not found: {path}")
        except Exception as e:
            send_telegram_message(chat_id, f"❌ Error reading file: {e}")
            print(f"❌ Error reading file: {e}")
        
    elif text.startswith("/build patch "):
        # Extract path
        path = text[13:].strip()
        
        # Store pending patch (next message will be the goal)
        PENDING_PATCHES[chat_id] = path
        
        send_telegram_message(chat_id, f"📝 Next message will be the goal for: {path}")
        print(f"✅ Waiting for goal message for {path}")
        
    else:
        # Unknown command
        help_msg = """Available commands:

/ping - Test connection
/status - System status
/build read <path> - Read file
/build patch <path> - Patch file (next message is goal)

Example:
/build read test.py"""
        
        send_telegram_message(chat_id, help_msg)
    
    return {"ok": True}


if __name__ == "__main__":
    import os, uvicorn
    PORT = int(os.getenv("PORT", "5000"))
    uvicorn.run("app.server:app", host="0.0.0.0", port=PORT)
