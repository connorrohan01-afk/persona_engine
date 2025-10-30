# content-scheduler

Lightweight scheduler that triggers your own webhooks with persona payloads on a cron or "every X minutes/hours" cadence. No external site automation here — just timed webhook delivery.

## Env
- AUTH_BEARER_TOKEN (default: `sched_token_123`)
- PORT (default 3000)

## Run
npm run dev

## Health (no auth)
curl -s https://<your-repl>.replit.app/api/v1/health | jq .

## Auth
Send header: `Authorization: Bearer sched_token_123`

## Create a schedule (every 30 minutes)
curl -s -X POST https://<your-repl>.replit.app/api/v1/schedules \
  -H "Authorization: Bearer sched_token_123" -H "Content-Type: application/json" \
  -d '{
    "personaId":"p_123",
    "channel":"generic",
    "webhookUrl":"https://example.com/hook",
    "payload":{"msg":"hello world"},
    "cadence":{"kind":"every","unit":"minutes","value":30},
    "enabled":true
  }'

## Create a cron schedule (every day 14:05 UTC)
curl -s -X POST https://<your-repl>.replit.app/api/v1/schedules \
  -H "Authorization: Bearer sched_token_123" -H "Content-Type: application/json" \
  -d '{
    "personaId":"writer01",
    "channel":"generic",
    "webhookUrl":"https://example.com/hook",
    "payload":{"topic":"daily post"},
    "cadence":{"kind":"cron","expr":"5 14 * * *"},
    "enabled":true
  }'

## Inspect
curl -s -H "Authorization: Bearer sched_token_123" https://<your-repl>.replit.app/api/v1/schedules | jq .
curl -s -H "Authorization: Bearer sched_token_123" https://<your-repl>.replit.app/api/v1/schedules/<id> | jq .
curl -s -H "Authorization: Bearer sched_token_123" https://<your-repl>.replit.app/api/v1/schedules/<id>/logs | jq .

## Update or disable
curl -s -X PATCH https://<your-repl>.replit.app/api/v1/schedules/<id> \
  -H "Authorization: Bearer sched_token_123" -H "Content-Type: application/json" \
  -d '{"enabled":false}'