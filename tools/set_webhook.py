#!/usr/bin/env python3
"""
One-time script to set Telegram webhook to Repl URL.
Calls Telegram setWebhook API to point to your deployment.
"""

import os
import sys
import httpx


def set_telegram_webhook():
    """Set the Telegram webhook URL."""
    
    # Get bot token from environment
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not found in environment")
        print("Please set the TELEGRAM_BOT_TOKEN secret in Replit Secrets")
        return False
    
    # Get Repl URL from environment
    repl_url = os.getenv("REPLIT_DOMAINS")
    
    if not repl_url:
        print("⚠️  WARNING: REPLIT_DOMAINS not found in environment")
        print("Please enter your Repl URL manually:")
        print("Example: https://your-repl-name.your-username.repl.co")
        manual_url = input("Repl URL: ").strip()
        
        if not manual_url:
            print("❌ ERROR: No URL provided")
            return False
        
        repl_url = manual_url
    else:
        # REPLIT_DOMAINS is a comma-separated list, take the first one
        repl_url = repl_url.split(",")[0].strip()
        # Add https:// if not present
        if not repl_url.startswith("http"):
            repl_url = f"https://{repl_url}"
    
    # Construct webhook URL
    webhook_url = f"{repl_url}/api/v1/telegram/{bot_token}"
    
    print(f"🔧 Setting Telegram webhook...")
    print(f"Bot Token: {bot_token[:10]}...{bot_token[-4:]}")
    print(f"Webhook URL: {webhook_url[:40]}...{webhook_url[-20:]}")
    
    # Call Telegram setWebhook API
    telegram_api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    
    try:
        response = httpx.post(
            telegram_api_url,
            json={
                "url": webhook_url,
                "max_connections": 40,
                "drop_pending_updates": True
            },
            timeout=15.0
        )
        
        result = response.json()
        
        if response.status_code == 200 and result.get("ok"):
            print(f"\n✅ Webhook set successfully!")
            print(f"Description: {result.get('description', 'N/A')}")
            
            # Get webhook info to verify
            info_response = httpx.get(
                f"https://api.telegram.org/bot{bot_token}/getWebhookInfo",
                timeout=10.0
            )
            
            if info_response.status_code == 200:
                info = info_response.json().get("result", {})
                print(f"\n📊 Webhook Info:")
                print(f"URL: {info.get('url', 'N/A')}")
                print(f"Pending updates: {info.get('pending_update_count', 0)}")
                print(f"Max connections: {info.get('max_connections', 'N/A')}")
                
                if info.get("last_error_date"):
                    print(f"⚠️  Last error: {info.get('last_error_message', 'N/A')}")
            
            return True
        else:
            print(f"\n❌ Failed to set webhook")
            print(f"Response: {result}")
            return False
            
    except Exception as e:
        print(f"\n❌ Error setting webhook: {e}")
        return False


def delete_webhook():
    """Delete the current webhook (useful for testing)."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not bot_token:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not found")
        return False
    
    try:
        response = httpx.post(
            f"https://api.telegram.org/bot{bot_token}/deleteWebhook",
            json={"drop_pending_updates": True},
            timeout=10.0
        )
        
        if response.status_code == 200:
            print("✅ Webhook deleted successfully")
            return True
        else:
            print(f"❌ Failed to delete webhook: {response.json()}")
            return False
            
    except Exception as e:
        print(f"❌ Error deleting webhook: {e}")
        return False


if __name__ == "__main__":
    print("🤖 Telegram Webhook Setup")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "delete":
        delete_webhook()
    else:
        success = set_telegram_webhook()
        
        if success:
            print("\n✅ Setup complete!")
            print("\nYou can now send commands to your Telegram bot:")
            print("  /ping - Test the bot")
            print("  /status - Check Manus status")
            print("  /build <task> - Enqueue a task")
        else:
            print("\n❌ Setup failed. Please check the errors above.")
            sys.exit(1)
