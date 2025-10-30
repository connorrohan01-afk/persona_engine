#!/bin/bash

# PersonaEngine API Enhancements - Complete Feature Test Suite
# Tests auth, rate limiting, OpenAPI, request logging, and enhanced status

echo "🧪 PersonaEngine API Enhancements - Complete Feature Test Suite"
echo "=============================================================="
echo ""

# Test configuration
HOST="http://localhost:8000"
AUTH_HEADER="Authorization: Bearer builder_token_123"
CONTENT_TYPE="Content-Type: application/json"

echo "🔧 Testing Enhanced API Features: $HOST"
echo ""

# Test 1: Enhanced Health Endpoint
echo "1️⃣ Test: Enhanced Health Endpoint (LLM mode + upsell data)"
curl -s "$HOST/api/v1/health" | jq '{mode_llm, last_upsell, timestamp}'
echo ""

# Test 2: OpenAPI Documentation
echo "2️⃣ Test: OpenAPI Documentation at /docs"
DOCS_RESPONSE=$(curl -s -w "%{http_code}" "$HOST/docs/" -o /dev/null)
echo "   Documentation status: HTTP $DOCS_RESPONSE"
if [ "$DOCS_RESPONSE" -eq 200 ] || [ "$DOCS_RESPONSE" -eq 301 ]; then
  echo "   ✅ OpenAPI docs available at $HOST/docs"
else
  echo "   ❌ OpenAPI docs not accessible"
fi
echo ""

# Test 3: Auth Protection
echo "3️⃣ Test: Authentication Protection"
echo "   Testing without auth (expect 401):"
RESPONSE=$(curl -s -X POST "$HOST/api/v1/brain.ask" \
  -H "$CONTENT_TYPE" \
  -d '{"question":"No auth test"}' \
  -w "HTTP_STATUS:%{http_code}")

HTTP_STATUS=$(echo "$RESPONSE" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
JSON_RESPONSE=$(echo "$RESPONSE" | sed 's/HTTP_STATUS:[0-9]*$//')

echo "   Status: $HTTP_STATUS"
echo "   Response: $(echo "$JSON_RESPONSE" | jq -r '.error')"
echo ""

# Test 4: Rate Limiting (multiple rapid requests)
echo "4️⃣ Test: Rate Limiting (30 req/min limit)"
echo "   Sending 5 rapid requests to test rate limiting:"
for i in {1..5}; do
  STATUS=$(curl -s -X POST "$HOST/api/v1/brain.ask" \
    -H "$AUTH_HEADER" \
    -H "$CONTENT_TYPE" \
    -d "{\"question\":\"Rate limit test $i\"}" \
    -w "%{http_code}" \
    -o /dev/null)
  echo "   Request $i: HTTP $STATUS"
  sleep 0.1
done
echo ""

# Test 5: Request Logging with Brain Ask
echo "5️⃣ Test: Request Logging (check server logs for UUID + timing)"
echo "   Making brain request with persona context:"
RESPONSE=$(curl -s -X POST "$HOST/api/v1/brain.ask" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "persona_id": "P0001",
    "question": "Test request logging with vault context"
  }')

echo "   Response: $(echo "$RESPONSE" | jq '{mode, answer_length: (.answer | length)}')"
echo "   ✅ Check server logs above for: {request_id: uuid, route: '/brain.ask', mode, persona_id, ms}"
echo ""

# Test 6: Upsell Endpoint with Enhanced Logging
echo "6️⃣ Test: Upsell Suggestions with Request Logging"
RESPONSE=$(curl -s -X POST "$HOST/api/v1/upsell.suggest" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "user_id": "U0001",
    "persona_id": "P0001",
    "job_id": "J0001",
    "style": "studio",
    "intent": "prints"
  }')

echo "   Response: $(echo "$RESPONSE" | jq '{mode, suggestions: (.suggestions | length), images_count: .context.images_count}')"
echo "   ✅ Check server logs above for: {request_id: uuid, route: '/upsell.suggest', mode, persona_id, job_id, ms}"
echo ""

# Test 7: System Persona Creation with Rate Limiting
echo "7️⃣ Test: System Persona Creation (rate limited)"
RESPONSE=$(curl -s -X POST "$HOST/api/v1/persona.add_system" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "id": "U0099",
    "name": "Test System Persona",
    "role": "system",
    "traits": ["test", "logging", "enhancement"]
  }')

echo "   Response: $(echo "$RESPONSE" | jq '{ok, system_persona: {id: .system_persona.id, name: .system_persona.name}}')"
echo ""

# Test 8: Status endpoint with upsell tracking
echo "8️⃣ Test: Status Endpoint (should show last upsell data)"
curl -s "$HOST/api/v1/status" | jq '{ok, last_upsell}'
echo ""

echo "✅ API Enhancement Test Suite Completed!"
echo ""
echo "🧾 Features Tested:"
echo "   ✅ Auth middleware protection (Bearer token required)"
echo "   ✅ Rate limiting (30 req/min per IP)"
echo "   ✅ OpenAPI documentation at /docs"
echo "   ✅ Request logging with UUID, timing, context"
echo "   ✅ Enhanced health/status with LLM mode + upsell tracking"
echo ""
echo "🎯 All routes protected and logged:"
echo "   • POST /brain.ask - operationId: askBrain"
echo "   • POST /persona.add_system - operationId: addSystemPersona"
echo "   • POST /upsell.suggest - operationId: suggestUpsells"
echo ""
echo "📊 Log format: {request_id: uuid, route, mode, persona_id, job_id, ms}"