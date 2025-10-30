#!/bin/bash

# PersonaEngine Schema Validation - Unit Smoke Tests
# Tests negative validation cases to ensure 400 responses instead of 500s

echo "🧪 PersonaEngine Schema Validation - Unit Smoke Tests"
echo "===================================================="
echo ""

# Test configuration
HOST="http://localhost:8000"
AUTH_HEADER="Authorization: Bearer builder_token_123"
CONTENT_TYPE="Content-Type: application/json"

echo "🔧 Testing Schema Validation: $HOST"
echo ""

# Test 1: Brain Ask - Missing question
echo "1️⃣ Test: Brain Ask - Missing question (expect 400)"
RESPONSE=$(curl -s -X POST "$HOST/api/v1/brain.ask" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{"persona_id":"P0001"}' \
  -w "HTTP_STATUS:%{http_code}")

HTTP_STATUS=$(echo "$RESPONSE" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
JSON_RESPONSE=$(echo "$RESPONSE" | sed 's/HTTP_STATUS:[0-9]*$//')

echo "   HTTP Status: $HTTP_STATUS"
echo "   Response: $JSON_RESPONSE" | jq '.'

# Test 2: Brain Ask - Empty question
echo ""
echo "2️⃣ Test: Brain Ask - Empty question (expect 400)"
RESPONSE=$(curl -s -X POST "$HOST/api/v1/brain.ask" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{"question":""}' \
  -w "HTTP_STATUS:%{http_code}")

HTTP_STATUS=$(echo "$RESPONSE" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
JSON_RESPONSE=$(echo "$RESPONSE" | sed 's/HTTP_STATUS:[0-9]*$//')

echo "   HTTP Status: $HTTP_STATUS"
echo "   Response: $JSON_RESPONSE" | jq '.'

# Test 3: Upsell Suggest - Missing user_id
echo ""
echo "3️⃣ Test: Upsell Suggest - Missing user_id (expect 400)"
RESPONSE=$(curl -s -X POST "$HOST/api/v1/upsell.suggest" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{"intent":"prints"}' \
  -w "HTTP_STATUS:%{http_code}")

HTTP_STATUS=$(echo "$RESPONSE" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
JSON_RESPONSE=$(echo "$RESPONSE" | sed 's/HTTP_STATUS:[0-9]*$//')

echo "   HTTP Status: $HTTP_STATUS"
echo "   Response: $JSON_RESPONSE" | jq '.'

# Test 4: Upsell Suggest - Empty user_id
echo ""
echo "4️⃣ Test: Upsell Suggest - Empty user_id (expect 400)"
RESPONSE=$(curl -s -X POST "$HOST/api/v1/upsell.suggest" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{"user_id":""}' \
  -w "HTTP_STATUS:%{http_code}")

HTTP_STATUS=$(echo "$RESPONSE" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
JSON_RESPONSE=$(echo "$RESPONSE" | sed 's/HTTP_STATUS:[0-9]*$//')

echo "   HTTP Status: $HTTP_STATUS"
echo "   Response: $JSON_RESPONSE" | jq '.'

# Test 5: Upsell Suggest - Invalid intent enum
echo ""
echo "5️⃣ Test: Upsell Suggest - Invalid intent enum (expect 400)"
RESPONSE=$(curl -s -X POST "$HOST/api/v1/upsell.suggest" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{"user_id":"U0001","intent":"invalid_intent"}' \
  -w "HTTP_STATUS:%{http_code}")

HTTP_STATUS=$(echo "$RESPONSE" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
JSON_RESPONSE=$(echo "$RESPONSE" | sed 's/HTTP_STATUS:[0-9]*$//')

echo "   HTTP Status: $HTTP_STATUS"
echo "   Response: $JSON_RESPONSE" | jq '.'

# Test 6: Persona Add System - Missing required fields
echo ""
echo "6️⃣ Test: Persona Add System - Missing name (expect 400)"
RESPONSE=$(curl -s -X POST "$HOST/api/v1/persona.add_system" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{"id":"U0002","role":"upsell"}' \
  -w "HTTP_STATUS:%{http_code}")

HTTP_STATUS=$(echo "$RESPONSE" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
JSON_RESPONSE=$(echo "$RESPONSE" | sed 's/HTTP_STATUS:[0-9]*$//')

echo "   HTTP Status: $HTTP_STATUS"
echo "   Response: $JSON_RESPONSE" | jq '.'

# Test 7: Persona Add System - Invalid ID format
echo ""
echo "7️⃣ Test: Persona Add System - Invalid ID format (expect 400)"
RESPONSE=$(curl -s -X POST "$HOST/api/v1/persona.add_system" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{"id":"INVALID123","name":"Test","role":"upsell"}' \
  -w "HTTP_STATUS:%{http_code}")

HTTP_STATUS=$(echo "$RESPONSE" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
JSON_RESPONSE=$(echo "$RESPONSE" | sed 's/HTTP_STATUS:[0-9]*$//')

echo "   HTTP Status: $HTTP_STATUS"
echo "   Response: $JSON_RESPONSE" | jq '.'

# Test 8: Persona Add System - Invalid role enum
echo ""
echo "8️⃣ Test: Persona Add System - Invalid role enum (expect 400)"
RESPONSE=$(curl -s -X POST "$HOST/api/v1/persona.add_system" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{"id":"U0003","name":"Test","role":"invalid_role"}' \
  -w "HTTP_STATUS:%{http_code}")

HTTP_STATUS=$(echo "$RESPONSE" | grep -o "HTTP_STATUS:[0-9]*" | cut -d: -f2)
JSON_RESPONSE=$(echo "$RESPONSE" | sed 's/HTTP_STATUS:[0-9]*$//')

echo "   HTTP Status: $HTTP_STATUS"
echo "   Response: $JSON_RESPONSE" | jq '.'

echo ""
echo "✅ Schema validation smoke tests completed!"
echo ""
echo "🧾 Summary:"
echo "   - All negative tests should return HTTP 400 (Bad Request)"
echo "   - Response format: {ok: false, error: 'descriptive message'}"
echo "   - No 500 Internal Server Errors should occur"