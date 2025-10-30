import { Router } from 'express';
import { parse, PlanCreateSchema, PlanPatchSchema } from '../lib/validators.js';
import { db, createOne, listMap, getOne, patchOne, deleteOne } from '../lib/store.js';

const r = Router();

r.post('/', (req, res) => {
  const v = parse(PlanCreateSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok:false, error: v.error });
  const rec = createOne(db.plans, v.data);
  res.json({ ok:true, data: rec });
});

r.get('/', (req, res) => {
  const offset = Number(req.query.offset || 0) || 0;
  const limit = Math.min(Number(req.query.limit || 50) || 50, 200);
  res.json({ ok:true, data: listMap(db.plans, { offset, limit }) });
});

r.get('/:id', (req, res) => {
  const rec = getOne(db.plans, req.params.id);
  if (!rec) return res.status(404).json({ ok:false, error:{ message:'not_found' }});
  res.json({ ok:true, data: rec });
});

r.patch('/:id', (req, res) => {
  const v = parse(PlanPatchSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok:false, error: v.error });
  const rec = patchOne(db.plans, req.params.id, v.data);
  if (!rec) return res.status(404).json({ ok:false, error:{ message:'not_found' }});
  res.json({ ok:true, data: rec });
});

r.delete('/:id', (req, res) => {
  const ok = deleteOne(db.plans, req.params.id);
  if (!ok) return res.status(404).json({ ok:false, error:{ message:'not_found' }});
  res.json({ ok:true, data: { id: req.params.id, deleted: true }});
});

export default r;