export const sleep = (ms) => new Promise(r => setTimeout(r, ms));

export function buildHeaders(regEntry) {
  const h = { ...(regEntry?.headers || {}), 'Content-Type': 'application/json' };
  if (regEntry?.token) h['Authorization'] = `Bearer ${regEntry.token}`;
  return h;
}

export function ok(data) { return { ok: true, data }; }
export function fail(message, extra = {}) { return { ok: false, error: { message, ...extra } }; }