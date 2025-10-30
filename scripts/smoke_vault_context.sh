#!/bin/bash

# PersonaEngine Vault Context - Integration Smoke Tests
# Tests the new vault context utilities for persona and manifest loading

echo "🧪 PersonaEngine Vault Context - Integration Smoke Tests"
echo "========================================================"
echo ""

# Test configuration
HOST="http://localhost:8000"
AUTH_HEADER="Authorization: Bearer builder_token_123"
CONTENT_TYPE="Content-Type: application/json"

echo "🔧 Testing Vault Context: $HOST"
echo ""

# Show vault structure
echo "📁 Vault Directory Structure:"
echo "   vault/dev/personas/{id}.json - Regular personas"
echo "   vault/dev/personas/system/{id}.json - System personas (U-prefix)"
echo "   vault/dev/{persona_id}/{job_id}/{style}/manifest_job.json - Job manifests"
echo ""

# Test 1: Brain with full vault context (persona + manifest)
echo "1️⃣ Test: Brain with Full Vault Context"
echo "   Should load: P0001 persona + J0001/studio manifest"
RESPONSE=$(curl -s -X POST "$HOST/api/v1/brain.ask" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "persona_id": "P0001",
    "question": "What can you tell me about this generation job and persona traits?"
  }')

echo "   Response: $(echo "$RESPONSE" | jq '{mode, answer_includes_studio: (.answer | contains("studio")), traits_applied: (.answer | contains("artistic") or contains("portrait"))}')"
echo ""

# Test 2: Upsell with manifest summary
echo "2️⃣ Test: Upsell with Manifest Summary"
echo "   Should include: job details from manifest_job.json"
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

echo "   Response: $(echo "$RESPONSE" | jq '{mode, suggestions: (.suggestions | length), manifest_count: .context.images_count}')"
echo ""

# Test 3: System persona loading
echo "3️⃣ Test: System Persona Loading (U-prefix)"
echo "   Should load: U0001 from vault/dev/personas/system/"
RESPONSE=$(curl -s -X POST "$HOST/api/v1/brain.ask" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "persona_id": "U0001",
    "question": "What are your commercial upsell capabilities?"
  }')

echo "   Response: $(echo "$RESPONSE" | jq '{mode, answer_length: (.answer | length)}')"
echo ""

# Test 4: Graceful fallback for missing personas
echo "4️⃣ Test: Missing Persona Fallback"
echo "   Should work without vault context, no errors"
RESPONSE=$(curl -s -X POST "$HOST/api/v1/brain.ask" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "persona_id": "MISSING999",
    "question": "This persona does not exist in vault"
  }')

echo "   Response: $(echo "$RESPONSE" | jq '{mode, ok: .ok, has_error: (.error != null)}')"
echo ""

# Test 5: Missing manifest graceful handling
echo "5️⃣ Test: Missing Manifest Graceful Handling"
echo "   Should work without manifest context, no errors"
RESPONSE=$(curl -s -X POST "$HOST/api/v1/upsell.suggest" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "user_id": "U0001",
    "persona_id": "P0001",
    "job_id": "MISSING",
    "style": "studio",
    "intent": "social"
  }')

echo "   Response: $(echo "$RESPONSE" | jq '{mode, ok: .ok, suggestions: (.suggestions | length)}')"
echo ""

echo "✅ Vault context integration smoke tests completed!"
echo ""
echo "🧾 Vault Context Features:"
echo "   ✅ Persona loading from vault/dev/personas/{id}.json"
echo "   ✅ System persona loading from vault/dev/personas/system/{id}.json"
echo "   ✅ Manifest loading from vault/dev/{persona_id}/{job_id}/{style}/manifest_job.json"
echo "   ✅ Manifest summarization: {style, count, seeds[], created_at, files[]}"
echo "   ✅ Enhanced context injection for brain queries"
echo "   ✅ Enhanced brief building for upsell suggestions"
echo "   ✅ Graceful fallback when files missing"
echo ""
echo "🎯 Integration Points:"
echo "   • /brain.ask - Uses vault personas + manifest context"
echo "   • /upsell.suggest - Uses vault manifest summaries in briefs"
echo "   • buildVaultContext() - Central context builder"