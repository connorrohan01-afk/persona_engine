import { Router } from 'express';
const r = Router();
r.get('/', (_req, res) => res.json({ ok:true, data:{ service:'persona-image-kit', status:'healthy' }}));
export default r;