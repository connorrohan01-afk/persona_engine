#!/bin/bash
# smoke:gen: curl to /gen using P0001
echo "🧪 Testing POST /gen with P0001..."
curl -X POST http://localhost:3000/api/v1/gen \
  -H "Content-Type: application/json" \
  -d '{
    "persona_id": "P0001",
    "style": "studio", 
    "count": 1,
    "slots": {
      "outfit": "test outfit",
      "mood": "confident", 
      "setting": "test studio"
    },
    "seed": 42
  }' | jq '.'