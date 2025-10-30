import express from 'express';
import helmet from 'helmet';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';
import { bearerAuth } from './src/lib/auth.js';
import healthRouter from './src/routes/health.js';
import schedulesRouter from './src/routes/schedules.js';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(helmet());
app.use(morgan('tiny'));
app.use(express.json({ limit: '1mb' }));

const limiter = rateLimit({ windowMs: 5 * 60 * 1000, max: 300, standardHeaders: true });
app.use(limiter);

// Public health
app.use('/api/v1/health', healthRouter);

// Protected routes
app.use('/api/v1/schedules', bearerAuth, schedulesRouter);

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
        const match = layer.regexp?.toString().match(/\/\^\\?\\\/(.*?)\\?\\\//);
        const prefix = match ? `/${match[1]}/` : '/';
        scan(layer.handle.stack, prefix.slice(0, -1));
      }
    });
  };
  if (app._router && app._router.stack) {
    scan(app._router.stack);
  } else {
    // Fallback routes
    routes.push('GET    /api/v1/health');
    routes.push('GET    /api/v1/schedules');
    routes.push('POST   /api/v1/schedules');
    routes.push('GET    /api/v1/schedules/:id');
    routes.push('PATCH  /api/v1/schedules/:id');
    routes.push('DELETE /api/v1/schedules/:id');
    routes.push('GET    /api/v1/schedules/:id/logs');
    routes.push('POST   /api/v1/schedules/_reload');
  }
  console.log('AVAILABLE_ROUTES');
  routes.sort().forEach(r => console.log(r));
}

app.listen(PORT, () => {
  console.log(`content-scheduler listening on :${PORT}`);
  printRoutes();
  console.log('READY: content-scheduler');
});

export default app;