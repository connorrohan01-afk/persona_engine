import { Router } from 'express';
import { listServices, listEvents } from '../lib/store.js';

const r = Router();
r.get('/', (_req, res) => {
  res.json({
    ok: true,
    data: {
      service: 'metrics-health',
      status: 'healthy',
      counts: { services: listServices().length, events: listEvents().length }
    }
  });
});
export default r;