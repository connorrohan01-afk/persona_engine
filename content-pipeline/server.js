import express from 'express';
import helmet from 'helmet';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';
import { bearerAuth } from './src/lib/auth.js';
import templatesRouter from './src/routes/templates.js';
import personasRouter from './src/routes/personas.js';
import plansRouter from './src/routes/plans.js';
import renderRouter from './src/routes/render.js';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(helmet());
app.use(morgan('tiny'));
app.use(express.json({ limit: '1mb' }));

const limiter = rateLimit({ windowMs: 5 * 60 * 1000, max: 200, standardHeaders: true });
app.use(limiter);

// Health (no auth)
app.get('/api/v1/health', (req, res) => {
  res.json({ ok: true, data: { service: 'content-pipeline', status: 'healthy' } });
});

// Protected routes
app.use('/api/v1/templates', bearerAuth, templatesRouter);
app.use('/api/v1/personas', bearerAuth, personasRouter);
app.use('/api/v1/plans', bearerAuth, plansRouter);
app.use('/api/v1/render', bearerAuth, renderRouter);

// 404
app.use((req, res) => res.status(404).json({ ok: false, error: { message: 'not_found' } }));

function printRoutes() {
  const routes = [];
  if (app._router && app._router.stack) {
    const push = (m, p) => {
      const methods = Object.keys(m.route.methods).map(x => x.toUpperCase()).join(',');
      routes.push(`${methods.padEnd(6)} ${p}${m.route.path}`);
    };
    app._router.stack.forEach((layer) => {
      if (layer.route?.path) {
        const methods = Object.keys(layer.route.methods).map(x => x.toUpperCase()).join(',');
        routes.push(`${methods.padEnd(6)} ${layer.route.path}`);
      } else if (layer.name === 'router' && layer.handle.stack) {
        const base = layer.regexp?.toString().match(/^\/\^(.*?)\//)?.[1]?.replace(/\\\//g,'/') || '';
        layer.handle.stack.forEach(h => h.route && push(h, `/${base}`));
      }
    });
  } else {
    // Fallback - manually list the known routes
    routes.push('GET    /api/v1/health');
    routes.push('GET    /api/v1/templates');
    routes.push('POST   /api/v1/templates');
    routes.push('GET    /api/v1/templates/:id');
    routes.push('PATCH  /api/v1/templates/:id');
    routes.push('DELETE /api/v1/templates/:id');
    routes.push('GET    /api/v1/personas');
    routes.push('POST   /api/v1/personas');
    routes.push('GET    /api/v1/personas/:id');
    routes.push('PATCH  /api/v1/personas/:id');
    routes.push('DELETE /api/v1/personas/:id');
    routes.push('GET    /api/v1/plans');
    routes.push('POST   /api/v1/plans');
    routes.push('GET    /api/v1/plans/:id');
    routes.push('PATCH  /api/v1/plans/:id');
    routes.push('DELETE /api/v1/plans/:id');
    routes.push('POST   /api/v1/render/preview');
  }
  console.log('AVAILABLE_ROUTES');
  routes.sort().forEach(r => console.log(r));
}

app.listen(PORT, () => {
  console.log(`content-pipeline listening on :${PORT}`);
  printRoutes();
  console.log('READY');
});

export default app;