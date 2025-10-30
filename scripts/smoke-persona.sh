#!/bin/bash
# smoke:persona: curl to /persona.new
echo "🧪 Testing POST /persona.new..."
curl -X POST http://localhost:3000/api/v1/persona.new \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Curl Test Persona",
    "traits": ["test", "curl", "automated"],
    "refs": ["curl_test"]
  }' | jq '.'