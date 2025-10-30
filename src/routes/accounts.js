import { Router } from 'express';
import { parse, AccountCreateSchema, AccountPatchSchema } from '../lib/validators.js';
import { createAccount, listAccounts, getAccount, patchAccount, deleteAccount, getProxy, getVault } from '../lib/store.js';

const r = Router();

// POST /accounts — create intake record
r.post('/', (req, res) => {
  const v = parse(AccountCreateSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });
  const { proxyId, vaultId } = v.data;

  if (proxyId && !getProxy(proxyId)) return res.status(400).json({ ok: false, error: { message: 'proxy_not_found' } });
  if (vaultId && !getVault(vaultId)) return res.status(400).json({ ok: false, error: { message: 'vault_not_found' } });

  const created = createAccount(v.data);
  console.log('[INTAKE] account created', created.id, created.platform, created.username);
  res.json({ ok: true, data: created });
});

// GET /accounts
r.get('/', (req, res) => {
  const offset = Number(req.query.offset || 0) || 0;
  const limit = Math.min(Number(req.query.limit || 50) || 50, 200);
  const list = listAccounts({ offset, limit });
  res.json({ ok: true, data: list });
});

// GET /accounts/:id
r.get('/:id', (req, res) => {
  const a = getAccount(req.params.id);
  if (!a) return res.status(404).json({ ok: false, error: { message: 'not_found' } });
  res.json({ ok: true, data: a });
});

// PATCH /accounts/:id — attach/update session/proxy/vault/status
r.patch('/:id', (req, res) => {
  const v = parse(AccountPatchSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });

  if (v.data.proxyId && !getProxy(v.data.proxyId)) return res.status(400).json({ ok: false, error: { message: 'proxy_not_found' } });
  if (v.data.vaultId && !getVault(v.data.vaultId)) return res.status(400).json({ ok: false, error: { message: 'vault_not_found' } });

  const updated = patchAccount(req.params.id, v.data);
  if (!updated) return res.status(404).json({ ok: false, error: { message: 'not_found' } });
  res.json({ ok: true, data: updated });
});

// DELETE /accounts/:id
r.delete('/:id', (req, res) => {
  const ok = deleteAccount(req.params.id);
  if (!ok) return res.status(404).json({ ok: false, error: { message: 'not_found' } });
  res.json({ ok: true, data: { id: req.params.id, deleted: true } });
});

export default r;