import express from 'express';
import helmet from 'helmet';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';
import healthRouter from './src/routes/health.js';
import signalsRouter from './src/routes/signals.js';
import metricsRouter from './src/routes/metrics.js';
import { bearerAuthOptional } from './src/lib/auth.js';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(helmet());
app.use(morgan('tiny'));
app.use(express.json({ limit: '1mb' }));

const limiter = rateLimit({ windowMs: 5 * 60 * 1000, max: 400, standardHeaders: true });
app.use(limiter);

// Public health
app.use('/api/v1/health', healthRouter);

// Signals + Metrics (write operations will enforce auth inside routers)
app.use('/api/v1/signals', bearerAuthOptional, signalsRouter);
app.use('/api/v1/metrics', bearerAuthOptional, metricsRouter);

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
    routes.push('POST   /api/v1/signals/register');
    routes.push('POST   /api/v1/signals/heartbeat');
    routes.push('PATCH  /api/v1/signals/status/:serviceId');
    routes.push('POST   /api/v1/signals/ping');
    routes.push('GET    /api/v1/metrics/summary');
    routes.push('GET    /api/v1/metrics/services');
    routes.push('GET    /api/v1/metrics/services/:id');
    routes.push('DELETE /api/v1/metrics/services/:id');
    routes.push('GET    /api/v1/metrics/events');
  }
  console.log('AVAILABLE_ROUTES');
  routes.sort().forEach(r => console.log(r));
}

app.listen(PORT, () => {
  console.log(`metrics-health listening on :${PORT}`);
  printRoutes();
  console.log('READY: metrics-health');
});

export default app;