import { Router } from 'express';
const r = Router();
r.get('/', (_req, res) => {
  res.json({ ok: true, data: { service: 'persona-router', status: 'healthy' } });
});
export default r;