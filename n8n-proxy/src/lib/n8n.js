import { fetch } from 'undici';

const base = (process.env.N8N_API_URL || '').replace(/\/+$/, '');
const apiKey = process.env.N8N_API_TOKEN || '';
const projectId = process.env.N8N_PROJECT_ID || '';

if (!base || !apiKey) {
  console.warn('[WARN] N8N_API_URL or N8N_API_TOKEN not set. Proxy calls will fail.');
}

function headers(extra = {}) {
  const h = {
    'X-N8N-API-KEY': apiKey,
    'content-type': 'application/json',
    ...extra,
  };
  if (projectId) h['n8n-project-id'] = projectId;
  return h;
}

export async function n8nGet(path) {
  const r = await fetch(`${base}${path}`, { method: 'GET', headers: headers() });
  const text = await r.text();
  let data; try { data = JSON.parse(text); } catch { data = text; }
  if (!r.ok) throw new Error(typeof data === 'object' ? JSON.stringify(data) : String(data));
  return data;
}

export async function n8nPost(path, body) {
  const r = await fetch(`${base}${path}`, {
    method: 'POST',
    headers: headers(),
    body: JSON.stringify(body ?? {}),
  });
  // n8n activate returns 204 sometimes; normalize
  if (r.status === 204) return { ok: true, data: null };
  const text = await r.text();
  let data; try { data = JSON.parse(text); } catch { data = text; }
  if (!r.ok) throw new Error(typeof data === 'object' ? JSON.stringify(data) : String(data));
  return data;
}