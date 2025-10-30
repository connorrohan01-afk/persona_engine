# governance-gateway

Enforces SAFE rate limits, per-persona caps, duplicate prevention, and exponential backoff. Does NOT automate third-party sites; only evaluates requests and returns allow/deny guidance.

## Env
- AUTH_BEARER_TOKEN (default: `gov_token_123`)
- PORT (default 3000)

## Run
npm run dev

## Endpoints
- GET    /api/v1/health               (public)
- PUT    /api/v1/limits               (auth) — upsert limit
- GET    /api/v1/limits/effective     (auth) — query effective limit
- GET    /api/v1/limits/stats         (auth) — system stats
- POST   /api/v1/decide               (auth) — evaluate request
- POST   /api/v1/admin/strike         (auth) — apply strike
- DELETE /api/v1/admin/backoff        (auth) — clear backoff
- GET    /api/v1/admin/stats          (auth) — admin stats

## Auth
`Authorization: Bearer gov_token_123` (or set your own secret)

## Usage Examples

### Set global limit
```bash
curl -s -X PUT https://HOST/api/v1/limits \
 -H "Authorization: Bearer gov_token_123" -H "Content-Type: application/json" \
 -d '{"action":"post","max":5,"windowMs":900000,"cost":1,"dedupeTtlMs":60000}'
```

### Set persona-specific limit
```bash
curl -s -X PUT https://HOST/api/v1/limits \
 -H "Authorization: Bearer gov_token_123" -H "Content-Type: application/json" \
 -d '{"action":"post","max":10,"windowMs":900000,"cost":1,"personaId":"p1"}'
```

### Check effective limit
```bash
curl -s "https://HOST/api/v1/limits/effective?personaId=p1&action=post" \
 -H "Authorization: Bearer gov_token_123"
```

### Make decision request
```bash
curl -s -X POST https://HOST/api/v1/decide \
 -H "Authorization: Bearer gov_token_123" -H "Content-Type: application/json" \
 -d '{"personaId":"p1","action":"post","cost":1,"dedupeKey":"post-123"}'
```

### Apply strike
```bash
curl -s -X POST https://HOST/api/v1/admin/strike \
 -H "Authorization: Bearer gov_token_123" -H "Content-Type: application/json" \
 -d '{"personaId":"p1","action":"post","reason":"spam_detected","weight":2}'
```

### Clear backoff
```bash
curl -s -X DELETE "https://HOST/api/v1/admin/backoff?personaId=p1&action=post" \
 -H "Authorization: Bearer gov_token_123"
```

## Decision Response Format
```json
{
  "ok": true,
  "data": {
    "allow": true,
    "waitForMs": 0,
    "reason": "ok",
    "tokensRemaining": 4,
    "nextAllowedAt": "2025-09-19T14:30:45.123Z",
    "windowEndsAt": "2025-09-19T14:45:45.123Z",
    "backoffMs": 0,
    "strikeLevel": 0
  }
}
```