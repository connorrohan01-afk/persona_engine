#!/bin/bash
# Post-Publish Verification Script
# Run this AFTER deployment status shows "Running"

set -e

PUBLIC_URL="https://${REPLIT_DEV_DOMAIN}"
BOT_TOKEN="${TELEGRAM_BOT_TOKEN}"
CHAT_ID="${TELEGRAM_CHAT_ID}"

echo "════════════════════════════════════════════════════════════════"
echo "POST-PUBLISH AUTOMATION"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Step 8: Reset webhook
echo "Step 8: Reset Telegram Webhook"
echo "────────────────────────────────────────────────────────────────"
python tools/reset_webhook.py
echo ""

# Check webhook info
echo "Webhook Info:"
WEBHOOK_INFO=$(curl -s "https://api.telegram.org/bot$BOT_TOKEN/getWebhookInfo")
echo "$WEBHOOK_INFO" | python3 -c "
import json, sys
data = json.load(sys.stdin)
result = data.get('result', {})
print(f'  Pending updates: {result.get(\"pending_update_count\", 0)}')
print(f'  Max connections: {result.get(\"max_connections\", 40)}')
print(f'  Last error: {result.get(\"last_error_message\") or \"None\"}')
"
echo ""

# Step 9: Public health check
echo "Step 9: Public Health Check"
echo "────────────────────────────────────────────────────────────────"
echo "GET $PUBLIC_URL/api/v1/health"
HEALTH_RESPONSE=$(curl -sv "$PUBLIC_URL/api/v1/health" 2>&1)
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | grep "< HTTP" | awk '{print $3}')
BODY=$(echo "$HEALTH_RESPONSE" | grep -A 100 "^{" | head -1)
echo "HTTP Status: $HTTP_CODE"
echo "Body: $BODY"
echo ""

# Step 10a: Test /ping
echo "Step 10a: Test /ping Command"
echo "────────────────────────────────────────────────────────────────"
echo "POST $PUBLIC_URL/api/v1/telegram/$BOT_TOKEN"
PING_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$PUBLIC_URL/api/v1/telegram/$BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"message\":{\"chat\":{\"id\":$CHAT_ID},\"text\":\"/ping\"}}")
HTTP_CODE=$(echo "$PING_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$PING_RESPONSE" | grep -v "HTTP_CODE:")
echo "HTTP Status: $HTTP_CODE"
echo "Body: $BODY"
echo ""

# Step 10b: Test /build read
echo "Step 10b: Test /build read test_sample.py"
echo "────────────────────────────────────────────────────────────────"
echo "POST $PUBLIC_URL/api/v1/telegram/$BOT_TOKEN"
READ_RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" -X POST "$PUBLIC_URL/api/v1/telegram/$BOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"message\":{\"chat\":{\"id\":$CHAT_ID},\"text\":\"/build read test_sample.py\"}}")
HTTP_CODE=$(echo "$READ_RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$READ_RESPONSE" | grep -v "HTTP_CODE:")
echo "HTTP Status: $HTTP_CODE"
echo "Body: $BODY"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "VERIFICATION COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "Check your Telegram chat for bot responses!"
echo "Then manually test:"
echo "  1. Send: /ping"
echo "  2. Send: /build read test_sample.py"
echo ""
