import express from 'express';
import helmet from 'helmet';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';
import { bearerAuth } from './src/lib/auth.js';
import healthRouter from './src/routes/health.js';
import limitsRouter from './src/routes/limits.js';
import decideRouter from './src/routes/decide.js';
import adminRouter from './src/routes/admin.js';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(helmet());
app.use(morgan('tiny'));
app.use(express.json({ limit: '1mb' }));
app.use(rateLimit({ windowMs: 5 * 60 * 1000, max: 400, standardHeaders: true }));

// Public
app.use('/api/v1/health', healthRouter);

// Protected
app.use('/api/v1/limits', bearerAuth, limitsRouter);
app.use('/api/v1/decide', bearerAuth, decideRouter);
app.use('/api/v1/admin', bearerAuth, adminRouter);

// 404
app.use((req, res) => res.status(404).json({ ok: false, error: { message: 'not_found' } }));

// Route printer
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
    lines.push('PUT    /api/v1/limits');
    lines.push('GET    /api/v1/limits/effective');
    lines.push('GET    /api/v1/limits/stats');
    lines.push('POST   /api/v1/decide');
    lines.push('POST   /api/v1/admin/strike');
    lines.push('DELETE /api/v1/admin/backoff');
    lines.push('GET    /api/v1/admin/stats');
  }
  console.log('AVAILABLE_ROUTES');
  lines.sort().forEach(l => console.log(l));
}

app.listen(PORT, () => {
  console.log(`governance-gateway listening on :${PORT}`);
  listRoutes();
  console.log('READY');
});

export default app;