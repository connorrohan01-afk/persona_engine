import express from 'express';
import helmet from 'helmet';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';
import telegramRouter from './src/routes/telegram.js';

const app = express();
const PORT = process.env.PORT || 3000;

// Security and middleware
app.use(helmet());
app.use(morgan('tiny'));
app.use(express.json({ limit: '1mb' }));

// Global rate limiting
const RATE_LIMIT_WINDOW_MS = parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 30000;
const RATE_LIMIT_MAX = parseInt(process.env.RATE_LIMIT_MAX) || 20;

app.use(rateLimit({ 
  windowMs: RATE_LIMIT_WINDOW_MS, 
  max: RATE_LIMIT_MAX, 
  standardHeaders: true,
  keyGenerator: (req) => {
    // Use chat ID for rate limiting if available
    return req.body?.message?.chat?.id?.toString() || req.ip;
  }
}));

// Routes
app.get('/api/v1/health', (req, res) => {
  res.json({ ok: true, data: { service: 'telegram-command-router' } });
});

app.use('/api/v1/telegram', telegramRouter);

// 404 handler
app.use((req, res) => {
  res.status(404).json({ ok: false, error: { message: 'not_found' } });
});

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
    lines.push('POST   /api/v1/telegram/webhook');
  }
  console.log('AVAILABLE_ROUTES');
  lines.sort().forEach(l => console.log(l));
}

app.listen(PORT, () => {
  console.log(`telegram-command-router listening on :${PORT}`);
  listRoutes();
  console.log('READY');
});

export default app;