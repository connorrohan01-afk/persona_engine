#!/bin/bash
# smoke:vault: curl to /vault.open
echo "🧪 Testing GET /vault.open..."
curl -s "http://localhost:3000/api/v1/vault.open?persona_id=P0001&job_id=J0001&style=studio" | jq '.'