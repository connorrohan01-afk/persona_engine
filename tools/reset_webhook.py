#!/usr/bin/env python3
"""
Reset Telegram webhook to point to the correct Replit URL.
This script:
1. Deletes the existing webhook
2. Sets a new webhook URL
3. Verifies the webhook configuration
"""

import os
import sys
import requests

# Get bot token
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ ERROR: TELEGRAM_BOT_TOKEN not found in environment")
    sys.exit(1)

# Default to content-maestro-connorrohan01.replit.app
REPL_URL = "https://content-maestro-connorrohan01.replit.app"

# Override from environment if available
env_url = os.getenv("REPLIT_DOMAINS")
if env_url:
    REPL_URL = env_url.split(",")[0].strip()
    if not REPL_URL.startswith("http"):
        REPL_URL = f"https://{REPL_URL}"

# Construct webhook URL
WEBHOOK_URL = f"{REPL_URL}/api/v1/telegram/{BOT_TOKEN}"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

print("\n" + "="*60)
print("🤖 Telegram Webhook Reset")
print("="*60)
print(f"Bot Token: {BOT_TOKEN[:10]}...{BOT_TOKEN[-4:]}")
print(f"Webhook URL: {WEBHOOK_URL}")
print("="*60 + "\n")

# Step 1: Delete existing webhook
print("1️⃣  Deleting existing webhook...")
try:
    response = requests.post(
        f"{BASE_URL}/deleteWebhook",
        json={"drop_pending_updates": True},
        timeout=10
    )
    result = response.json()
    print(f"   Delete result: {result}")
except Exception as e:
    print(f"   ⚠️  Error deleting webhook: {e}")

print()

# Step 2: Set new webhook
print("2️⃣  Setting new webhook...")
try:
    response = requests.post(
        f"{BASE_URL}/setWebhook",
        json={
            "url": WEBHOOK_URL,
            "max_connections": 40,
            "drop_pending_updates": True
        },
        timeout=10
    )
    result = response.json()
    print(f"   Set result: {result}")
    
    if result.get("ok"):
        print(f"   ✅ Webhook set successfully!")
    else:
        print(f"   ❌ Failed to set webhook: {result.get('description')}")
except Exception as e:
    print(f"   ❌ Error setting webhook: {e}")

print()

# Step 3: Verify webhook
print("3️⃣  Verifying webhook configuration...")
try:
    response = requests.get(f"{BASE_URL}/getWebhookInfo", timeout=10)
    result = response.json()
    
    if result.get("ok"):
        info = result.get("result", {})
        print(f"   URL: {info.get('url', 'N/A')}")
        print(f"   Pending updates: {info.get('pending_update_count', 0)}")
        print(f"   Max connections: {info.get('max_connections', 'N/A')}")
        
        if info.get("last_error_date"):
            print(f"   ⚠️  Last error: {info.get('last_error_message')}")
        else:
            print(f"   ✅ No errors")
    else:
        print(f"   Info result: {result}")
except Exception as e:
    print(f"   ❌ Error getting webhook info: {e}")

print()
print("="*60)
print("✅ Webhook reset complete!")
print("="*60)
print()
print("Next steps:")
print(f"1. Visit: {REPL_URL}/api/v1/health")
print("2. Send /ping to your Telegram bot")
print("3. Test /build read <path> and /build patch <path> commands")
print()
