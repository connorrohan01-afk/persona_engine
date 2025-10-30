#!/usr/bin/env python3
"""
Simplified FastAPI server for Telegram webhook integration.
Token-agnostic webhook with built-in diagnostics.
"""

from fastapi import FastAPI, Request
import os
import json
import time
import requests
from queue import Queue
from threading import Thread
from common.telegram import send_message

# Configuration
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Task queue
TASK_Q = Queue()

# FastAPI app
app = FastAPI(title="Telegram Integration")


# Worker thread
def worker():
    """Background worker that processes queued tasks."""
    print("✅ Worker thread started")
    while True:
        try:
            task = TASK_Q.get(timeout=1.0)
            print(f"Worker processing: {task}")
            
            # Process task (placeholder for SDK runner integration)
            task_type = task.get("type")
            if task_type == "build":
                print(f"BUILD: {task.get('payload')}")
            
            TASK_Q.task_done()
        except Exception as e:
            # Timeout or error - continue loop
            pass


# Start worker thread
Thread(target=worker, daemon=True).start()


@app.post("/api/v1/telegram/{token}")
async def telegram_webhook(token: str, request: Request):
    """
    Token-agnostic webhook endpoint.
    Validates token and processes Telegram updates.
    """
    # Validate token
    if token != BOT_TOKEN:
        print(f"WARNING: Invalid token received: {token[:10]}...")
        return {"ok": True, "ignored": True}
    
    # Parse update
    update = await request.json()
    
    # Log inbound message
    print(f"INBOUND {time.time()} {json.dumps(update)[:800]}")
    
    # Extract message
    msg = update.get("message") or {}
    text = (msg.get("text") or "").strip()
    chat_id = str(msg.get("chat", {}).get("id") or CHAT_ID)
    
    if not text:
        return {"ok": True}
    
    # Handle commands
    if text.startswith("/ping"):
        print(f"Processing /ping from {chat_id}")
        send_message(chat_id, "✅ Direct test pong")
        
    elif text.startswith("/status"):
        print(f"Processing /status from {chat_id}")
        status_msg = f"📊 System OK | Queue: {TASK_Q.qsize()}"
        send_message(chat_id, status_msg)
        
    elif text.startswith("/build"):
        print(f"Processing /build from {chat_id}")
        build_task = text[6:].strip() or "default"
        TASK_Q.put({"type": "build", "payload": build_task})
        send_message(chat_id, f"🛠️ Queued build task: {build_task}")
    
    else:
        # Unknown command
        help_msg = """Available commands:

/ping - Test connection
/status - System status
/build <task> - Queue build task

Try: /ping"""
        send_message(chat_id, help_msg)
    
    return {"ok": True}


@app.get("/api/v1/health")
def health():
    """Health check endpoint."""
    return {
        "ok": True,
        "queue_depth": TASK_Q.qsize(),
        "time": time.time()
    }


@app.get("/api/v1/telegram/info")
def telegram_info():
    """
    Get Telegram webhook info directly from Telegram API.
    Useful for diagnostics.
    """
    if not BOT_TOKEN:
        return {"error": "TELEGRAM_BOT_TOKEN not configured"}
    
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo"
        response = requests.get(url, timeout=10)
        return response.json()
    except Exception as e:
        return {"error": str(e)}


@app.on_event("startup")
async def startup():
    """Startup logging."""
    print("\n" + "="*60)
    print("🚀 Telegram Webhook Server")
    print("="*60)
    print(f"✅ Worker thread running")
    print(f"✅ Webhook endpoint: /api/v1/telegram/{{token}}")
    print(f"✅ Health check: /api/v1/health")
    print(f"✅ Diagnostics: /api/v1/telegram/info")
    print("="*60 + "\n")


    if __name__ == "__main__":
        import os, uvicorn
        PORT = int(os.getenv("PORT", "5000"))
        uvicorn.run("app.server:app", host="0.0.0.0", port=PORT)
