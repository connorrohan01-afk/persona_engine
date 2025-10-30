import { Router } from 'express';
import { parse, JobCreateSchema } from '../lib/validators.js';
import { addJob, q } from '../lib/queue.js';

const r = Router();

// POST /jobs
r.post('/', async (req, res) => {
  const v = parse(JobCreateSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });
  try {
    const j = await addJob(v.data);
    res.json({ ok: true, data: { id: j.id, name: j.name, opts: j.opts } });
  } catch (e) {
    res.status(500).json({ ok: false, error: { message: e.message } });
  }
});

// GET /jobs/:id
r.get('/:id', async (req, res) => {
  try {
    const j = await q.getJob(req.params.id);
    if (!j) return res.status(404).json({ ok: false, error: { message: 'not_found' } });
    res.json({ ok: true, data: { id: j.id, name: j.name, state: await j.getState(), returnvalue: j.returnvalue } });
  } catch (e) {
    res.status(500).json({ ok: false, error: { message: e.message } });
  }
});

// GET /jobs
r.get('/', async (_req, res) => {
  try {
    const jobs = await q.getJobs(['waiting','active','completed','failed'], 0, 50, true);
    const data = jobs.map(j => ({ id: j.id, name: j.name, state: j.state }));
    res.json({ ok: true, data });
  } catch (e) {
    res.status(500).json({ ok: false, error: { message: e.message } });
  }
});

// DELETE /jobs/:id
r.delete('/:id', async (req, res) => {
  try {
    const j = await q.getJob(req.params.id);
    if (!j) return res.status(404).json({ ok: false, error: { message: 'not_found' } });
    await j.remove();
    res.json({ ok: true, data: { id: req.params.id, deleted: true } });
  } catch (e) {
    res.status(500).json({ ok: false, error: { message: e.message } });
  }
});

export default r;