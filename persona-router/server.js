import express from 'express';
import helmet from 'helmet';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';
import { requireBearer } from './src/lib/auth.js';
import routerApi from './src/routes/router.js';
import registryApi from './src/routes/registry.js';
import healthApi from './src/routes/health.js';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(helmet());
app.use(morgan('tiny'));
app.use(express.json({ limit: '1mb' }));

const limiter = rateLimit({ windowMs: 5 * 60 * 1000, max: 300, standardHeaders: true });
app.use(limiter);

// Public health
app.use('/api/v1/health', healthApi);

// Registry (auth)
app.use('/api/v1/registry', requireBearer, registryApi);

// Router (auth)
app.use('/api/v1/router', requireBearer, routerApi);

// 404
app.use((req, res) => res.status(404).json({ ok: false, error: { message: 'not_found' } }));

function printRoutes() {
  const routes = [];
  const scan = (stack, base = '') => {
    stack.forEach((layer) => {
      if (layer.route) {
        const m = Object.keys(layer.route.methods).map(x => x.toUpperCase()).join(',');
        routes.push(`${m.padEnd(6)} ${base}${layer.route.path}`);
      } else if (layer.name === 'router' && layer.handle?.stack) {
        const prefix = '/api/v1'; // simplified for route printing
        scan(layer.handle.stack, prefix);
      }
    });
  };
  if (app._router && app._router.stack) {
    scan(app._router.stack);
  } else {
    // Fallback routes
    routes.push('GET    /api/v1/health');
    routes.push('GET    /api/v1/registry');
    routes.push('POST   /api/v1/registry');
    routes.push('GET    /api/v1/registry/:id');
    routes.push('DELETE /api/v1/registry/:id');
    routes.push('POST   /api/v1/router');
  }
  console.log('AVAILABLE_ROUTES');
  routes.sort().forEach(r => console.log(r));
}

app.listen(PORT, () => {
  console.log(`persona-router listening on :${PORT}`);
  printRoutes();
  console.log('READY: persona-router');
});

export default app;