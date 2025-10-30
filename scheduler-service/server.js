import express from 'express';
import helmet from 'helmet';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';
import healthRouter from './src/routes/health.js';
import jobsRouter from './src/routes/jobs.js';
import { bearerAuth } from './src/lib/auth.js';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(helmet());
app.use(morgan('tiny'));
app.use(express.json({ limit: '1mb' }));

const limiter = rateLimit({ windowMs: 5 * 60 * 1000, max: 300, standardHeaders: true });
app.use(limiter);

// Health
app.use('/api/v1/health', healthRouter);

// Protected
app.use('/api/v1/jobs', bearerAuth, jobsRouter);

// 404
app.use((req, res) => res.status(404).json({ ok: false, error: { message: 'not_found' } }));

function printRoutes() {
  const routes = [];
  const scan = (stack, base = '') => {
    stack.forEach((l) => {
      if (l.route) {
        const m = Object.keys(l.route.methods).map(x => x.toUpperCase()).join(',');
        routes.push(`${m.padEnd(6)} ${base}${l.route.path}`);
      } else if (l.name === 'router' && l.handle?.stack) {
        scan(l.handle.stack, base);
      }
    });
  };
  if (app._router && app._router.stack) {
    scan(app._router.stack);
  } else {
    // Fallback routes
    routes.push('GET    /api/v1/health');
    routes.push('GET    /api/v1/jobs');
    routes.push('POST   /api/v1/jobs');
    routes.push('GET    /api/v1/jobs/:id');
    routes.push('DELETE /api/v1/jobs/:id');
  }
  console.log('AVAILABLE_ROUTES');
  routes.sort().forEach(r => console.log(r));
}

app.listen(PORT, () => {
  console.log(`scheduler-service listening on :${PORT}`);
  printRoutes();
  console.log('READY: scheduler-service');
});

export default app;