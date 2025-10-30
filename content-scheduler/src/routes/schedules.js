import { Router } from 'express';
import { parse, ScheduleCreateSchema, SchedulePatchSchema, QueryListSchema } from '../lib/validators.js';
import { createSchedule, patchSchedule, getSchedule, listSchedules, deleteSchedule, getLogs } from '../lib/store.js';
import { startRunnerFor, stopCron, refreshRunners } from '../lib/runner.js';

const r = Router();

// Create
r.post('/', (req, res) => {
  const v = parse(ScheduleCreateSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });

  const created = createSchedule(v.data);
  startRunnerFor(created);
  res.json({ ok: true, data: created });
});

// List
r.get('/', (req, res) => {
  const q = parse(QueryListSchema, req.query || {});
  if (!q.ok) return res.status(400).json({ ok: false, error: q.error });
  res.json({ ok: true, data: listSchedules(q.data) });
});

// Get one
r.get('/:id', (req, res) => {
  const s = getSchedule(req.params.id);
  if (!s) return res.status(404).json({ ok: false, error: { message: 'not_found' } });
  res.json({ ok: true, data: s });
});

// Patch
r.patch('/:id', (req, res) => {
  const v = parse(SchedulePatchSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok: false, error: v.error });

  const updated = patchSchedule(req.params.id, v.data);
  if (!updated) return res.status(404).json({ ok: false, error: { message: 'not_found' } });

  // if cadence/enabled changed, refresh this runner
  stopCron(updated.id);
  startRunnerFor(updated);
  res.json({ ok: true, data: updated });
});

// Delete
r.delete('/:id', (req, res) => {
  const s = getSchedule(req.params.id);
  if (!s) return res.status(404).json({ ok: false, error: { message: 'not_found' } });
  stopCron(s.id);
  deleteSchedule(s.id);
  res.json({ ok: true, data: { id: s.id, deleted: true } });
});

// Logs
r.get('/:id/logs', (req, res) => {
  const s = getSchedule(req.params.id);
  if (!s) return res.status(404).json({ ok: false, error: { message: 'not_found' } });
  const limit = Math.min(Number(req.query.limit || 50) || 50, 200);
  res.json({ ok: true, data: getLogs(s.id, limit) });
});

// Reload all runners (admin)
r.post('/_reload', (_req, res) => {
  refreshRunners();
  res.json({ ok: true, data: { reloaded: true } });
});

export default r;