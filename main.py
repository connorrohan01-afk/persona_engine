#!/usr/bin/env python3
"""
Single-process FastAPI Telegram bot launcher.
Minimal and deterministic file operations via Claude AI.
"""

import os
import sys

def main():
    """Launch the FastAPI Telegram file bot"""
    print("🚀 Telegram File Bot - Single Process")
    print("📡 FastAPI with Claude AI file operations...")
    
    # Set environment defaults
    os.environ.setdefault("PORT", "5000")
    
    # Check required environment variables
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
    
    print(f"🌐 Port: {os.environ.get('PORT', '5000')}")
    print(f"🤖 Telegram Bot: {'✅ configured' if bot_token else '❌ missing'}")
    print(f"🧠 Anthropic API: {'✅ configured' if anthropic_key else '❌ missing'}")
    print()
    
    if not bot_token:
        print("❌ ERROR: TELEGRAM_BOT_TOKEN not found in environment")
        sys.exit(1)
    
    if not anthropic_key:
        print("⚠️  WARNING: ANTHROPIC_API_KEY not found (patch operations will fail)")
    
    # Launch the FastAPI server
    try:
        print("✅ Starting Telegram file bot server...")
        print("🔍 Health check: http://localhost:5000/api/v1/health")
        print()
        
        # Import and run FastAPI app
        import uvicorn
        from app.server import app
        
        uvicorn.run(
            app, 
            host="0.0.0.0", 
            port=int(os.environ.get("PORT", "5000")),
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n⏹️ Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()