import axios from 'axios';
import { sleep, buildHeaders } from './util.js';

export async function forwardJson({ baseUrl, path, method = 'POST', body = {}, headers = {}, timeoutMs = 5000, attempts = 2, baseMs = 200 }) {
  let lastErr = null;
  for (let i = 0; i <= attempts; i++) {
    try {
      const t0 = Date.now();
      const res = await axios.request({
        url: `${baseUrl.replace(/\/$/, '')}/${path.replace(/^\//, '')}`,
        method,
        data: body,
        headers,
        timeout: timeoutMs,
        validateStatus: () => true
      });
      const ms = Date.now() - t0;
      return { ok: true, status: res.status, ms, data: res.data };
    } catch (e) {
      lastErr = e;
      if (i < attempts) await sleep(baseMs * Math.pow(2, i));
    }
  }
  return { ok: false, status: 0, ms: null, error: lastErr?.message || 'request_failed' };
}

export function routePlan(tool, action) {
  // central place to define target paths per (tool, action)
  const table = {
    persona: {
      build: { path: '/api/v1/persona/build', method: 'POST' },
      update: { path: '/api/v1/persona/update', method: 'PATCH' }
    },
    scheduler: {
      schedule: { path: '/api/v1/jobs/schedule', method: 'POST' },
      cancel: { path: '/api/v1/jobs/cancel', method: 'POST' }
    },
    vault: {
      put: { path: '/api/v1/blobs', method: 'POST' },
      get: { path: '/api/v1/blobs/get', method: 'POST' }
    },
    intake: {
      create: { path: '/api/v1/accounts', method: 'POST' },
      update: { path: '/api/v1/accounts/update', method: 'POST' }
    },
    notify: {
      heartbeat: { path: '/api/v1/signals/heartbeat', method: 'POST' },
      register: { path: '/api/v1/signals/register', method: 'POST' }
    },
    raw: {}
  };
  return table[tool]?.[action] || null;
}