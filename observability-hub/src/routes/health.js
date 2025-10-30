import { Router } from 'express';
const r = Router();
r.get('/', (req, res) => {
  res.json({ ok: true, data: { service: 'observability-hub', status: 'healthy', time: new Date().toISOString() } });
});
export default r;