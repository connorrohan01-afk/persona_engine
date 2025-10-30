# content-pipeline

Templates + personas + plans + safe, local interpolation preview. No external calls.

## Env
- AUTH_BEARER_TOKEN (default: `pipeline_token_123`)
- PORT=3000

## Run

npm run dev

## Health (no auth)

curl -s https://.replit.app/api/v1/health

## Auth header

`Authorization: Bearer pipeline_token_123`

## Quick flow

Create a template:
```
curl -s -X POST https://.replit.app/api/v1/templates \
-H "Authorization: Bearer pipeline_token_123" -H "Content-Type: application/json" \
-d '{"name":"promo","body":"Top {{subreddit}} picks: {{title}}","variables":["subreddit","title"]}'
```

Create a persona:
```
curl -s -X POST https://.replit.app/api/v1/personas \
-H "Authorization: Bearer pipeline_token_123" -H "Content-Type: application/json" \
-d '{"name":"Crisp","voice":"concise","tone":"helpful","rules":["no emojis"]}'
```

Create a plan:
```
curl -s -X POST https://.replit.app/api/v1/plans \
-H "Authorization: Bearer pipeline_token_123" -H "Content-Type: application/json" \
-d '{"accountId":"acct_1","templateId":"<TEMPLATE_ID>","personaId":"<PERSONA_ID>","variables":{"subreddit":"pics","title":"Sunset"}}'
```

Preview (by planId):
```
curl -s -X POST https://.replit.app/api/v1/render/preview \
-H "Authorization: Bearer pipeline_token_123" -H "Content-Type: application/json" \
-d '{"planId":"<PLAN_ID>"}'
```

Preview (raw):
```
curl -s -X POST https://.replit.app/api/v1/render/preview \
-H "Authorization: Bearer pipeline_token_123" -H "Content-Type: application/json" \
-d '{"body":"Hello {{name}}","variables":{"name":"world"},"voice":"friendly","tone":"casual"}'
```