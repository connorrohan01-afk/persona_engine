import express from 'express';
import helmet from 'helmet';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';
import { bearerAuth } from './src/lib/auth.js';
import healthRouter from './src/routes/health.js';
import eventsRouter from './src/routes/events.js';
import metricsRouter from './src/routes/metrics.js';
import reportRouter from './src/routes/report.js';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(helmet());
app.use(morgan('tiny'));
app.use(express.json({ limit: '1mb' }));
app.use(rateLimit({ windowMs: 5 * 60 * 1000, max: 300, standardHeaders: true }));

// Public health
app.use('/api/v1/health', healthRouter);

// Protected
app.use('/api/v1/events', bearerAuth, eventsRouter);
app.use('/api/v1/metrics', bearerAuth, metricsRouter);
app.use('/api/v1/report', bearerAuth, reportRouter);

// 404
app.use((req, res) => res.status(404).json({ ok: false, error: { message: 'not_found' } }));

// Route listing
function listRoutes() {
  const lines = [];
  if (app._router && app._router.stack) {
    app._router.stack.forEach((layer) => {
      if (layer.route) {
        const methods = Object.keys(layer.route.methods).map(m => m.toUpperCase()).join(',');
        lines.push(`${methods.padEnd(6)} ${layer.route.path}`);
      } else if (layer.name === 'router' && layer.handle.stack) {
        layer.handle.stack.forEach((h) => {
          if (h.route) {
            const methods = Object.keys(h.route.methods).map(m => m.toUpperCase()).join(',');
            let base = layer.regexp?.toString() || '';
            base = base.replace(/^\/\^\\/, '/').replace(/\\\/\?\$.*$/, '');
            lines.push(`${methods.padEnd(6)} ${base}${h.route.path}`);
          }
        });
      }
    });
  } else {
    // Fallback routes
    lines.push('GET    /api/v1/health');
    lines.push('POST   /api/v1/events');
    lines.push('GET    /api/v1/metrics');
    lines.push('POST   /api/v1/metrics/counter');
    lines.push('POST   /api/v1/metrics/gauge');
    lines.push('GET    /api/v1/report');
    lines.push('GET    /api/v1/report/events');
  }
  console.log('AVAILABLE_ROUTES');
  lines.sort().forEach(l => console.log(l));
}

app.listen(PORT, () => {
  console.log(`observability-hub listening on :${PORT}`);
  listRoutes();
  console.log('READY');
});

export default app;