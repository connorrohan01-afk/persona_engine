#!/bin/bash
# smoke:more: curl to /gen.more
echo "🧪 Testing POST /gen.more..."
curl -X POST http://localhost:3000/api/v1/gen.more \
  -H "Content-Type: application/json" \
  -d '{
    "persona_id": "P0001",
    "job_id": "J0001",
    "count": 1
  }' | jq '.'