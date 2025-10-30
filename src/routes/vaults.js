import { Router } from 'express';
import { parse, VaultCreateSchema } from '../lib/validators.js';
import { createVault, listVaults, getVault, patchVault, deleteVault } from '../lib/store.js';

const r = Router();

// POST /vaults
r.post('/', (req, res) => {
  if (process.env.USE_MOCK_VAULT === 'false') {
    // placeholder for swapping in a real secrets adapter later
  }
  const v = parse(VaultCreateSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });
  const created = createVault(v.data);
  res.json({ ok: true, data: created });
});

// GET /vaults
r.get('/', (req, res) => res.json({ ok: true, data: listVaults() }));

// GET /vaults/:id
r.get('/:id', (req, res) => {
  const v = getVault(req.params.id);
  if (!v) return res.status(404).json({ ok: false, error: { message: 'not_found' } });
  res.json({ ok: true, data: v });
});

// PATCH /vaults/:id
r.patch('/:id', (req, res) => {
  const vlt = patchVault(req.params.id, req.body || {});
  if (!vlt) return res.status(404).json({ ok: false, error: { message: 'not_found' } });
  res.json({ ok: true, data: vlt });
});

// DELETE /vaults/:id
r.delete('/:id', (req, res) => {
  const ok = deleteVault(req.params.id);
  if (!ok) return res.status(404).json({ ok: false, error: { message: 'not_found' } });
  res.json({ ok: true, data: { id: req.params.id, deleted: true } });
});

export default r;