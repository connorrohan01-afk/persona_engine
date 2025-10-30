import { Router } from 'express';
import { parse, RegistryUpsertSchema, IdParamSchema } from '../lib/validators.js';
import { upsertService, listServices, getService, deleteService } from '../lib/registry.js';

const r = Router();

r.get('/', (_req, res) => res.json({ ok: true, data: listServices() }));

r.post('/', (req, res) => {
  const v = parse(RegistryUpsertSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });
  const rec = upsertService(v.data);
  res.json({ ok: true, data: rec });
});

r.get('/:id', (req, res) => {
  const v = parse(IdParamSchema, req.params);
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });
  const rec = getService(v.data.id);
  if (!rec) return res.status(404).json({ ok: false, error: { message: 'not_found' } });
  res.json({ ok: true, data: rec });
});

r.delete('/:id', (req, res) => {
  const v = parse(IdParamSchema, req.params);
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });
  const ok = deleteService(v.data.id);
  if (!ok) return res.status(404).json({ ok: false, error: { message: 'not_found' } });
  res.json({ ok: true, data: { id: v.data.id, deleted: true } });
});

export default r;