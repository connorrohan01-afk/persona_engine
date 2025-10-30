import { Router } from 'express';
import { parse, PreviewSchema } from '../lib/validators.js';
import { db, getOne, appendHistory } from '../lib/store.js';
import { interpolate, applyPersona } from '../lib/render.js';

const r = Router();

// POST /render/preview — preview by planId OR raw template/body + variables
r.post('/preview', (req, res) => {
  const v = parse(PreviewSchema, req.body || {});
  if (!v.ok) return res.status(400).json({ ok:false, error: v.error });

  let body = v.data.body;
  let variables = v.data.variables || {};
  let persona = null;

  if (!body && v.data.planId) {
    const plan = getOne(db.plans, v.data.planId);
    if (!plan) return res.status(404).json({ ok:false, error:{ message:'plan_not_found' }});
    const tmpl = getOne(db.templates, plan.templateId);
    if (!tmpl) return res.status(404).json({ ok:false, error:{ message:'template_not_found' }});
    body = tmpl.body;
    variables = { ...(plan.variables || {}) };
    if (plan.personaId) persona = getOne(db.personas, plan.personaId);
  } else if (!body && v.data.templateId) {
    const tmpl = getOne(db.templates, v.data.templateId);
    if (!tmpl) return res.status(404).json({ ok:false, error:{ message:'template_not_found' }});
    body = tmpl.body;
  }

  // Allow explicit persona override fields
  if (!persona && (v.data.personaId || v.data.personaName || v.data.voice || v.data.tone)) {
    persona = {
      id: v.data.personaId || 'override',
      name: v.data.personaName || 'override',
      voice: v.data.voice || 'neutral',
      tone: v.data.tone || 'informative'
    };
  }

  const output = applyPersona(interpolate(body || '', variables), persona);
  const rec = appendHistory({ planId: v.data.planId || null, output, createdAt: new Date().toISOString() });

  res.json({ ok:true, data: { previewId: rec.id, output }});
});

export default r;