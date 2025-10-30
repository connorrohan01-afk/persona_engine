import { Router } from 'express';
import { listSchedules } from '../lib/store.js';

const r = Router();
r.get('/', (_req, res) => {
  res.json({ ok: true, data: { service: 'content-scheduler', status: 'healthy', schedules: listSchedules().length } });
});
export default r;