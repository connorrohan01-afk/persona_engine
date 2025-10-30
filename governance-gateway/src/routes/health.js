import { Router } from 'express';
import { stats } from '../lib/store.js';
const r = Router();
r.get('/', (req, res) => {
  res.json({ ok: true, data: { service: 'governance-gateway', status: 'healthy', time: new Date().toISOString(), stats: stats() } });
});
export default r;