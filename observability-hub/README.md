# observability-hub

Aggregates events, counters, gauges, and persona snapshots from internal services. No external calls.

## Env
- AUTH_BEARER_TOKEN (default: `obs_token_123`)
- PORT (default 3000)

## Run
npm run dev

## Endpoints
- GET  /api/v1/health               (public)
- POST /api/v1/events               (auth)  — ingest event(s)
- GET  /api/v1/metrics              (auth)  — read counters & gauges
- POST /api/v1/metrics/counter      (auth)  — { key, delta }
- POST /api/v1/metrics/gauge        (auth)  — { key, value }
- GET  /api/v1/report               (auth)  — window + optional personaId
- GET  /api/v1/report/events        (auth)  — recent events (optional ?since=ISO)

## Auth
`Authorization: Bearer obs_token_123` (or set your own secret)

## Quick test (replace HOST with your replit URL)
curl -s https://HOST/api/v1/health

# ingest one event
curl -s -X POST https://HOST/api/v1/events \
 -H "Authorization: Bearer obs_token_123" -H "Content-Type: application/json" \
 -d '{"type":"post_success","personaId":"p1","accountId":"a1","platform":"reddit"}'

# bump a counter
curl -s -X POST https://HOST/api/v1/metrics/counter \
 -H "Authorization: Bearer obs_token_123" -H "Content-Type: application/json" \
 -d '{"key":"posts.success","delta":1}'

# set a gauge
curl -s -X POST https://HOST/api/v1/metrics/gauge \
 -H "Authorization: Bearer obs_token_123" -H "Content-Type: application/json" \
 -d '{"key":"queue.depth","value":7}'

# read metrics
curl -s -H "Authorization: Bearer obs_token_123" https://HOST/api/v1/metrics

# get a 24h report (global)
curl -s -H "Authorization: Bearer obs_token_123" "https://HOST/api/v1/report?window=24h"

# get a 7d report for a persona
curl -s -H "Authorization: Bearer obs_token_123" "https://HOST/api/v1/report?window=7d&personaId=p1"