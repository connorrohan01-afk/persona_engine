#!/bin/bash

# PersonaEngine Prompt Templates - Smoke Test
# Tests the new brain_system.txt and upsell_system.txt templates

echo "🧪 PersonaEngine Prompt Templates - Smoke Test"
echo "=============================================="
echo ""

# Test configuration
HOST="http://localhost:8000"
AUTH_HEADER="Authorization: Bearer builder_token_123"
CONTENT_TYPE="Content-Type: application/json"

echo "🔧 Testing Prompt Templates: $HOST"
echo ""

# Test 1: Brain Template with Persona Traits
echo "1️⃣ Test: Brain Template with Persona Context"
echo "   Should use: 'Studio Brain: concise assistant, <=120 words'"
curl -s -X POST "$HOST/api/v1/brain.ask" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "persona_id": "P0001",
    "question": "What can you tell me about studio photography best practices?",
    "context": {"vault_summary": "User has 15 studio sessions completed"}
  }' | jq '{mode, answer_length: (.answer | length), starts_with_brain: (.answer | startswith("Based") or startswith("For") or startswith("Studio"))}'

echo ""

# Test 2: Upsell Template Detection
echo "2️⃣ Test: Upsell Template Detection"
echo "   Should use: 'GBT upsell assistant, 3 tailored offers'"
curl -s -X POST "$HOST/api/v1/upsell.suggest" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "user_id": "U0001",
    "persona_id": "P0001",
    "job_id": "J0001",
    "style": "studio",
    "intent": "prints"
  }' | jq '{mode, suggestion_count: (.suggestions | length), first_title: .suggestions[0].title}'

echo ""

# Test 3: Brain Without Persona (Should Still Use Template)
echo "3️⃣ Test: Brain Template Without Persona"
echo "   Should still use brain_system.txt template"
curl -s -X POST "$HOST/api/v1/brain.ask" \
  -H "$AUTH_HEADER" \
  -H "$CONTENT_TYPE" \
  -d '{
    "question": "How does the vault storage work?"
  }' | jq '{mode, answer_length: (.answer | length)}'

echo ""
echo "✅ Prompt template smoke tests completed!"
echo ""
echo "📋 Template Files:"
echo "   • prompts/brain_system.txt - <=120 words, bullet points"
echo "   • prompts/upsell_system.txt - 3 offers, max 6 word titles"
echo ""
echo "🎯 System Prompt Composition:"
echo "   • Base template + persona traits injection"
echo "   • Automatic context detection (brain vs upsell)"
echo "   • Response trimming in Claude adapter"