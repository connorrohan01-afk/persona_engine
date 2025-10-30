import express from 'express';
import helmet from 'helmet';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';
import { bearerAuth } from './src/lib/auth.js';
import accountsRouter from './src/routes/accounts.js';
import proxiesRouter from './src/routes/proxies.js';
import vaultsRouter from './src/routes/vaults.js';
import n8nRouter from './src/routes/n8n.js';
import buildRouter from './src/routes/build.js';

const app = express();
const PORT = 3000; // Fixed port for internal microservice (proxied by FastAPI)

// Trust proxy for rate limiting and headers
app.set('trust proxy', 1);

app.use(helmet());
app.use(morgan('tiny'));
app.use(express.json({ limit: '1mb' }));

const limiter = rateLimit({ windowMs: 5 * 60 * 1000, max: 200, standardHeaders: true });
app.use(limiter);

// Health (no auth)
app.get('/api/v1/health', (req, res) => {
  res.json({ ok: true, data: { service: 'account-intake', status: 'healthy' } });
});

// Protected routes
app.use('/api/v1/accounts', bearerAuth, accountsRouter);
app.use('/api/v1/proxies', bearerAuth, proxiesRouter);
app.use('/api/v1/vaults', bearerAuth, vaultsRouter);
app.use('/api/v1/n8n', bearerAuth, n8nRouter);
app.use('/api/v1', bearerAuth, buildRouter);

// 404
app.use((req, res) => res.status(404).json({ ok: false, error: { message: 'not_found' } }));

// Route print
function printRoutes() {
  const routes = [];
  if (app._router && app._router.stack) {
    app._router.stack.forEach((m) => {
      if (m.route && m.route.path) {
        const methods = Object.keys(m.route.methods).map(m => m.toUpperCase()).join(',');
        routes.push(`${methods.padEnd(6)} ${m.route.path}`);
      } else if (m.name === 'router' && m.handle.stack) {
        m.handle.stack.forEach((h) => {
          if (h.route) {
            const methods = Object.keys(h.route.methods).map(m => m.toUpperCase()).join(',');
            const path = `${m.regexp?.toString().replace(/^\/\^/, '').replace(/\$\/$/, '') || '/api/v1'}${h.route.path}`;
            routes.push(`${methods.padEnd(6)} ${path}`);
          }
        });
      }
    });
  } else {
    // Fallback - manually list the known routes
    routes.push('GET    /api/v1/health');
    routes.push('GET    /api/v1/accounts');
    routes.push('POST   /api/v1/accounts');
    routes.push('GET    /api/v1/accounts/:id');
    routes.push('PATCH  /api/v1/accounts/:id');
    routes.push('DELETE /api/v1/accounts/:id');
    routes.push('GET    /api/v1/proxies');
    routes.push('POST   /api/v1/proxies');
    routes.push('GET    /api/v1/proxies/:id');
    routes.push('PATCH  /api/v1/proxies/:id');
    routes.push('DELETE /api/v1/proxies/:id');
    routes.push('GET    /api/v1/vaults');
    routes.push('POST   /api/v1/vaults');
    routes.push('GET    /api/v1/vaults/:id');
    routes.push('PATCH  /api/v1/vaults/:id');
    routes.push('DELETE /api/v1/vaults/:id');
    routes.push('POST   /api/v1/n8n/create');
    routes.push('POST   /api/v1/n8n/activate/:id');
    routes.push('GET    /api/v1/n8n/get/:id');
  }
  console.log('AVAILABLE_ROUTES');
  routes.sort().forEach(r => console.log(r));
}

app.listen(PORT, () => {
  console.log(`account-intake listening on :${PORT}`);
  printRoutes();
  console.log('READY');
});

export default app;