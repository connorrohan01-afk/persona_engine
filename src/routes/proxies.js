import { Router } from 'express';
import { parse, ProxySchema } from '../lib/validators.js';
import { createProxy, listProxies, getProxy, patchProxy, deleteProxy } from '../lib/store.js';

const r = Router();

// POST /proxies
r.post('/', (req, res) => {
  if (process.env.USE_MOCK_PROXY === 'false') {
    // still no real connectivity here; just a flag for future adapter swap
  }
  const v = parse(ProxySchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });
  const created = createProxy(v.data);
  res.json({ ok: true, data: created });
});

// GET /proxies
r.get('/', (req, res) => res.json({ ok: true, data: listProxies() }));

// GET /proxies/:id
r.get('/:id', (req, res) => {
  const p = getProxy(req.params.id);
  if (!p) return res.status(404).json({ ok: false, error: { message: 'not_found' } });
  res.json({ ok: true, data: p });
});

// PATCH /proxies/:id
r.patch('/:id', (req, res) => {
  const p = patchProxy(req.params.id, req.body || {});
  if (!p) return res.status(404).json({ ok: false, error: { message: 'not_found' } });
  res.json({ ok: true, data: p });
});

// DELETE /proxies/:id
r.delete('/:id', (req, res) => {
  const ok = deleteProxy(req.params.id);
  if (!ok) return res.status(404).json({ ok: false, error: { message: 'not_found' } });
  res.json({ ok: true, data: { id: req.params.id, deleted: true } });
});

export default r;