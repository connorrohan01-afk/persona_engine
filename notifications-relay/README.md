# notifications-relay

Small relay that forwards internal events to Telegram or Email, with a safe MOCK default.

## Env
- AUTH_BEARER_TOKEN (default `relay_token_123`)
- TELEGRAM_BOT_TOKEN (optional; enable Telegram)
- SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS (optional; enable Email)
- RELAY_FROM (optional; default "Notifications <no-reply@example.com>")
- PORT (default 3000)

## Run
npm run dev

## Health
curl -s https://<your-repl>.replit.app/api/v1/health

## Test (MOCK, no external sends)
curl -s -X POST https://<your-repl>.replit.app/api/v1/notify/test \
  -H "Authorization: Bearer relay_token_123" -H "Content-Type: application/json" \
  -d '{"channel":"mock","to":"demo","message":"hello from relay"}'

## Telegram (requires TELEGRAM_BOT_TOKEN)
curl -s -X POST https://<your-repl>.replit.app/api/v1/notify/test \
  -H "Authorization: Bearer relay_token_123" -H "Content-Type: application/json" \
  -d '{"channel":"telegram","to":7484907544,"message":"it works ✅"}'

## Email (requires SMTP env)
curl -s -X POST https://<your-repl>.replit.app/api/v1/notify/test \
  -H "Authorization: Bearer relay_token_123" -H "Content-Type: application/json" \
  -d '{"channel":"email","to":"you@example.com","message":"it works ✅"}'

## Multi-channel event
curl -s -X POST https://<your-repl>.replit.app/api/v1/notify/event \
  -H "Authorization: Bearer relay_token_123" -H "Content-Type: application/json" \
  -d '{"type":"cluster.activate","severity":"info","message":"Cluster A live","channels":[{"channel":"mock","to":"log"},{"channel":"telegram","to":7484907544}]}'