# persona-image-kit

Local-only image tools for personas: avatars, text overlays, simple transforms, and a basic meme renderer. No external APIs.

## Env
- AUTH_BEARER_TOKEN (default: `img_token_123`)
- PORT=3000

## Run

npm run dev

## Health (no auth)

curl -s https://.replit.app/api/v1/health

## Auth header

`Authorization: Bearer img_token_123`

## Examples

### Avatar

```bash
curl -s -X POST https://.replit.app/api/v1/images/avatar \
-H "Authorization: Bearer img_token_123" -H "Content-Type: application/json" \
-d '{"initials":"KD","size":512,"bg":"#111827","fg":"#F9FAFB"}' | jq .
```

### Overlay

```bash
curl -s -X POST https://.replit.app/api/v1/images/overlay \
-H "Authorization: Bearer img_token_123" -H "Content-Type: application/json" \
-d '{"text":"hello world","width":800,"height":400,"bg":"#0B1020","fg":"#E5E7EB","fontSize":64}' | jq .
```

### Transform (resize)

```bash
DATA=$(base64 -w0 sample.png); 
curl -s -X POST https://.replit.app/api/v1/images/transform \
-H "Authorization: Bearer img_token_123" -H "Content-Type: application/json" \
-d "{\"imageBase64\":\"data:image/png;base64,${DATA}\",\"ops\":[{\"type\":\"resize\",\"w\":400}],\"output\":\"file\"}" | jq .
```

### Meme

```bash
curl -s -X POST https://.replit.app/api/v1/renders/meme \
-H "Authorization: Bearer img_token_123" -H "Content-Type: application/json" \
-d '{"topText":"TOP LINE","bottomText":"BOTTOM LINE","width":800,"height":800,"bg":"#000000","fg":"#FFFFFF"}' | jq .
```