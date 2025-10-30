#!/bin/bash

# PersonaEngine Brain Smoke Test
# Tests the /api/v1/brain.ask endpoint with persona context

echo "🧠 PersonaEngine Brain - Smoke Test"
echo "==================================="
echo ""

# Test configuration
HOST="http://localhost:8000"
AUTH_HEADER="Authorization: Bearer builder_token_123"
CONTENT_TYPE="Content-Type: application/json"

echo "📡 Testing Brain Endpoint: $HOST/api/v1/brain.ask"
echo ""

# Test 1: Basic question without persona
echo "1️⃣ Test: Basic question (no persona)"
echo "   Question: 'What is PersonaEngine?'"
curl -s -X POST "$HOST/api/v1/brain.ask" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "question": "What is PersonaEngine?"
  }' | jq '.'

echo ""
echo "2️⃣ Test: Question with persona context"
echo "   Question: 'What'\''s in the latest job manifest for P0001?'"
curl -s -X POST "$HOST/api/v1/brain.ask" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "persona_id": "P0001",
    "question": "What'\''s in the latest job manifest for P0001?"
  }' | jq '.'

echo ""
echo "3️⃣ Test: Authentication failure (no Bearer token)"
echo "   Expected: 401 Unauthorized"
curl -s -X POST "$HOST/api/v1/brain.ask" \
  -H "$CONTENT_TYPE" \
  -d '{
    "question": "Test question"
  }' | jq '.'

echo ""
echo "4️⃣ Test: Bad request (missing question)"
echo "   Expected: 400 Bad Request"
curl -s -X POST "$HOST/api/v1/brain.ask" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "persona_id": "P0001"
  }' | jq '.'

echo ""
echo "5️⃣ Test: Style analysis question"
echo "   Question: 'Explain the studio style generation settings'"
curl -s -X POST "$HOST/api/v1/brain.ask" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "question": "Explain the studio style generation settings",
    "context": {"style": "studio"}
  }' | jq '.'

echo ""
echo "✅ Brain smoke tests completed!"