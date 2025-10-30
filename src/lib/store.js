import { nanoid } from 'nanoid';

const accounts = new Map(); // id -> account
const proxies = new Map();  // id -> proxy
const vaults  = new Map();  // id -> vault
const n8nWorkflows = new Map(); // id -> n8n workflow

export const db = { accounts, proxies, vaults, n8nWorkflows };

// ACCOUNT helpers
export function createAccount(payload) {
  const id = nanoid();
  const now = new Date().toISOString();
  const acct = {
    id,
    createdAt: now,
    updatedAt: now,
    status: 'intake',
    ...payload
  };
  accounts.set(id, acct);
  return acct;
}
export function listAccounts({ offset = 0, limit = 50 } = {}) {
  const all = Array.from(accounts.values());
  return { total: all.length, items: all.slice(offset, offset + limit) };
}
export function getAccount(id) { return accounts.get(id) || null; }
export function patchAccount(id, patch) {
  const cur = accounts.get(id);
  if (!cur) return null;
  const updated = { ...cur, ...patch, updatedAt: new Date().toISOString() };
  accounts.set(id, updated);
  return updated;
}
export function deleteAccount(id) { return accounts.delete(id); }

// PROXY helpers (no real networking)
export function createProxy(payload) {
  const id = nanoid();
  const now = new Date().toISOString();
  const p = { id, createdAt: now, updatedAt: now, healthy: true, ...payload };
  proxies.set(id, p);
  return p;
}
export function listProxies() { return Array.from(proxies.values()); }
export function getProxy(id) { return proxies.get(id) || null; }
export function patchProxy(id, patch) {
  const cur = proxies.get(id);
  if (!cur) return null;
  const updated = { ...cur, ...patch, updatedAt: new Date().toISOString() };
  proxies.set(id, updated);
  return updated;
}
export function deleteProxy(id) { return proxies.delete(id); }

// VAULT helpers (mock)
export function createVault(payload) {
  const id = nanoid();
  const now = new Date().toISOString();
  const v = { id, createdAt: now, updatedAt: now, ...payload };
  vaults.set(id, v);
  return v;
}
export function listVaults() { return Array.from(vaults.values()); }
export function getVault(id) { return vaults.get(id) || null; }
export function patchVault(id, patch) {
  const cur = vaults.get(id);
  if (!cur) return null;
  const updated = { ...cur, ...patch, updatedAt: new Date().toISOString() };
  vaults.set(id, updated);
  return updated;
}
export function deleteVault(id) { return vaults.delete(id); }

// N8N WORKFLOW helpers
export function createN8nWorkflow(payload) {
  const id = nanoid();
  const now = new Date().toISOString();
  const workflow = {
    id,
    createdAt: now,
    updatedAt: now,
    status: 'created',
    ...payload
  };
  n8nWorkflows.set(id, workflow);
  return workflow;
}

export function getN8nWorkflow(id) {
  return n8nWorkflows.get(id) || null;
}

export function updateN8nWorkflow(id, updates) {
  const current = n8nWorkflows.get(id);
  if (!current) return null;
  const updated = {
    ...current,
    ...updates,
    updatedAt: new Date().toISOString()
  };
  n8nWorkflows.set(id, updated);
  return updated;
}