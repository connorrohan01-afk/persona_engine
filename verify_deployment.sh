#!/bin/bash
# Verify Telegram Bot Deployment
# Run this script AFTER publishing to verify everything works

set -e

PUBLIC_URL="https://${REPLIT_DEV_DOMAIN}"
BOT_TOKEN="${TELEGRAM_BOT_TOKEN}"
CHAT_ID="${TELEGRAM_CHAT_ID}"

echo "════════════════════════════════════════════════════════════════"
echo "DEPLOYMENT VERIFICATION SCRIPT"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Step 1: Health Check
echo "Step 1: Testing Public Health Endpoint"
echo "────────────────────────────────────────────────────────────────"
HEALTH_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "$PUBLIC_URL/api/v1/health")
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$HEALTH_RESPONSE" | grep -v "HTTP_CODE:")

if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ Health: $BODY"
else
  echo "❌ Health check failed: HTTP $HTTP_CODE"
  echo "   Deployment is not live yet. Please check deployment status."
  exit 1
fi
echo ""

# Step 2: Reset Webhook
echo "Step 2: Resetting Telegram Webhook"
echo "────────────────────────────────────────────────────────────────"
python tools/reset_webhook.py
echo ""

# Step 3: Check Webhook Info
echo "Step 3: Verifying Webhook Configuration"
echo "────────────────────────────────────────────────────────────────"
WEBHOOK_INFO=$(curl -s "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo")
echo "$WEBHOOK_INFO" | python3 -c "
import json, sys
data = json.load(sys.stdin)
result = data.get('result', {})
url = result.get('url', '')
token_part = url.split('/')[-1] if url else ''
masked = token_part[:3] + '...' + token_part[-3:] if len(token_part) > 6 else token_part
url_masked = url.replace(token_part, masked) if token_part else url
print(f'Webhook URL: {url_masked}')
print(f'Pending updates: {result.get(\"pending_update_count\", 0)}')
print(f'Last error: {result.get(\"last_error_message\") or \"None\"}')
"
echo ""

# Step 4: Test /ping via webhook simulation
echo "Step 4: Testing /ping Command (Simulated Webhook)"
echo "────────────────────────────────────────────────────────────────"
PING_RESPONSE=$(curl -s -X POST "$PUBLIC_URL/api/v1/telegram/$BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"message\":{\"chat\":{\"id\":$CHAT_ID},\"text\":\"/ping\"}}")
echo "Response: $PING_RESPONSE"
echo ""

# Step 5: Test /build read via webhook simulation
echo "Step 5: Testing /build read Command (Simulated Webhook)"
echo "────────────────────────────────────────────────────────────────"
READ_RESPONSE=$(curl -s -X POST "$PUBLIC_URL/api/v1/telegram/$BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"message\":{\"chat\":{\"id\":$CHAT_ID},\"text\":\"/build read test_sample.py\"}}")
echo "Response: $READ_RESPONSE"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "VERIFICATION COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Next steps:"
echo "1. Check your Telegram chat for the bot replies"
echo "2. Send '/ping' from Telegram to test real webhook"
echo "3. Send '/build read test_sample.py' to test file reading"
echo ""
echo "If you don't see replies in Telegram, check the deployment logs"
echo "for errors in the Replit Deployments panel."
echo ""
