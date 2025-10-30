const REG = new Map();
// sensible defaults you can replace at runtime via /registry
// example keys only; leave empty by default
export function upsertService({ serviceId, baseUrl, token, headers, meta }) {
  const now = new Date().toISOString();
  const rec = {
    serviceId,
    baseUrl,
    token: token || null,
    headers: headers || {},
    meta: meta || {},
    updatedAt: now,
    createdAt: REG.get(serviceId)?.createdAt || now
  };
  REG.set(serviceId, rec);
  return rec;
}
export function getService(serviceId) { return REG.get(serviceId) || null; }
export function listServices() { return Array.from(REG.values()); }
export function deleteService(serviceId) { return REG.delete(serviceId); }

// default mapping for tool → serviceId
export function resolveServiceId(tool, overrideId) {
  if (overrideId) return overrideId;
  const map = {
    persona: 'persona-core',
    scheduler: 'content-scheduler',
    vault: 'vaults',
    intake: 'account-intake',
    notify: 'metrics-health',
    raw: 'persona-core'
  };
  return map[tool] || 'persona-core';
}