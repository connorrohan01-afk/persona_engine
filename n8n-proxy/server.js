import express from 'express';
import helmet from 'helmet';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';
import n8nRouter from './src/routes/n8n.js';
import { bearerAuth } from './src/lib/auth.js';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(helmet());
app.use(morgan('tiny'));
app.use(express.json({ limit: '1mb' }));

const limiter = rateLimit({ windowMs: 5 * 60 * 1000, max: 200, standardHeaders: true });
app.use(limiter);

// Health (no auth)
app.get('/api/v1/health', (req, res) => {
  res.json({ ok: true, data: { service: 'n8n-proxy', status: 'healthy' } });
});

// Protected n8n proxy routes
app.use('/api/v1/n8n', bearerAuth, n8nRouter);

// 404
app.use((req, res) => res.status(404).json({ ok: false, error: { message: 'not_found' } }));

function listRoutes() {
  const lines = [];
  if (app._router && app._router.stack) {
    app._router.stack.forEach((s) => {
      if (s.route) {
        const methods = Object.keys(s.route.methods).map(m => m.toUpperCase()).join(',');
        lines.push(`${methods.padEnd(6)} ${s.route.path}`);
      } else if (s.name === 'router' && s.handle?.stack) {
        s.handle.stack.forEach(h => {
          if (h.route) {
            const methods = Object.keys(h.route.methods).map(m => m.toUpperCase()).join(',');
            lines.push(`${methods.padEnd(6)} /api/v1/n8n${h.route.path}`);
          }
        });
      }
    });
  } else {
    // Fallback routes
    lines.push('GET    /api/v1/health');
    lines.push('GET    /api/v1/n8n/workflows/:id');
    lines.push('POST   /api/v1/n8n/activate');
    lines.push('POST   /api/v1/n8n/create');
  }
  console.log('AVAILABLE_ROUTES');
  lines.sort().forEach(l => console.log(l));
}

app.listen(PORT, () => {
  console.log(`n8n-proxy listening on :${PORT}`);
  listRoutes();
  console.log('PROXY READY');
});

export default app;