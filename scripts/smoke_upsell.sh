#!/bin/bash

# PersonaEngine GBT Upsell Assistant - Smoke Test
# Tests the system persona creation and upsell suggestion endpoints

echo "💰 PersonaEngine GBT Upsell Assistant - Smoke Test"
echo "=================================================="
echo ""

# Test configuration
HOST="http://localhost:8000"
AUTH_HEADER="Authorization: Bearer builder_token_123"
CONTENT_TYPE="Content-Type: application/json"

echo "🔧 Testing Upsell System: $HOST"
echo ""

# Test 1: Create GBT system persona
echo "1️⃣ Test: Create GBT system persona"
echo "   Creating system persona with ID: U0001, role: upsell"
curl -s -X POST "$HOST/api/v1/persona.add_system" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "id": "U0001",
    "name": "GBT",
    "role": "upsell",
    "traits": ["helpful", "commercial", "concise"]
  }' | jq '.'

echo ""
echo "2️⃣ Test: Upsell suggestion with vault context"
echo "   User: GBT, Persona: P0001, Job: J0001, Intent: prints"
curl -s -X POST "$HOST/api/v1/upsell.suggest" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "user_id": "U0001",
    "persona_id": "P0001",
    "job_id": "J0001",
    "style": "studio",
    "intent": "prints",
    "tone": "friendly"
  }' | jq '.'

echo ""
echo "3️⃣ Test: Upsell suggestion for social media"
echo "   User: GBT, Intent: social"
curl -s -X POST "$HOST/api/v1/upsell.suggest" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "user_id": "U0001",
    "intent": "social",
    "tone": "assertive"
  }' | jq '.'

echo ""
echo "4️⃣ Test: Upsell suggestion for follow-up shoots"
echo "   User: GBT, Intent: followup"
curl -s -X POST "$HOST/api/v1/upsell.suggest" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "user_id": "U0001",
    "persona_id": "P0001",
    "job_id": "J0001",
    "style": "studio",
    "intent": "followup",
    "tone": "friendly"
  }' | jq '.'

echo ""
echo "5️⃣ Test: Authentication failure (no Bearer token)"
echo "   Expected: 401 Unauthorized"
curl -s -X POST "$HOST/api/v1/upsell.suggest" \
  -H "$CONTENT_TYPE" \
  -d '{
    "user_id": "U0001",
    "intent": "prints"
  }' | jq '.'

echo ""
echo "6️⃣ Test: Bad request (missing user_id)"
echo "   Expected: 400 Bad Request"
curl -s -X POST "$HOST/api/v1/upsell.suggest" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "intent": "prints"
  }' | jq '.'

echo ""
echo "7️⃣ Test: Invalid system persona ID (no U prefix)"
echo "   Expected: 400 Bad Request"
curl -s -X POST "$HOST/api/v1/persona.add_system" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "id": "INVALID01",
    "name": "Bad Persona",
    "role": "test",
    "traits": ["invalid"]
  }' | jq '.'

echo ""
echo "✅ GBT Upsell smoke tests completed!"
echo ""
echo "🧾 Summary:"
echo "   - System persona creation (U0001 GBT)"
echo "   - Vault context reading (P0001/J0001/studio)"
echo "   - Intent-based suggestions (prints, social, followup)"
echo "   - Authentication and validation testing"
echo "   - Deterministic template fallback mode"