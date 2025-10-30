import express from 'express';
import helmet from 'helmet';
import morgan from 'morgan';
import path from 'path';
import { fileURLToPath } from 'url';
import rateLimit from 'express-rate-limit';
import { bearerAuth } from './src/lib/auth.js';
import imagesRouter from './src/routes/images.js';
import rendersRouter from './src/routes/renders.js';
import healthRouter from './src/routes/health.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;

app.use(helmet());
app.use(morgan('tiny'));
app.use(express.json({ limit: '2mb' }));
app.use('/public', express.static(path.join(__dirname, 'public')));

const limiter = rateLimit({ windowMs: 5 * 60 * 1000, max: 200, standardHeaders: true });
app.use(limiter);

// Health (no auth)
app.use('/api/v1/health', healthRouter);

// Protected routes
app.use('/api/v1/images', bearerAuth, imagesRouter);
app.use('/api/v1/renders', bearerAuth, rendersRouter);

// 404
app.use((req, res) => res.status(404).json({ ok:false, error:{ message:'not_found' }}));

function printRoutes() {
  const routes = [];
  const push = (m, base) => {
    const methods = Object.keys(m.route.methods).map(x=>x.toUpperCase()).join(',');
    routes.push(`${methods.padEnd(6)} ${base}${m.route.path}`);
  };
  if (app._router && app._router.stack) {
    app._router.stack.forEach(layer => {
      if (layer.route?.path) {
        const methods = Object.keys(layer.route.methods).map(x=>x.toUpperCase()).join(',');
        routes.push(`${methods.padEnd(6)} ${layer.route.path}`);
      } else if (layer.name === 'router' && layer.handle.stack) {
        const base = (layer.regexp?.toString().match(/^\/\^(.*?)\//)?.[1] || '').replace(/\\\//g,'/');
        layer.handle.stack.forEach(h => h.route && push(h, `/${base}`));
      }
    });
  } else {
    // Fallback routes
    routes.push('GET    /api/v1/health');
    routes.push('POST   /api/v1/images/avatar');
    routes.push('POST   /api/v1/images/overlay');
    routes.push('POST   /api/v1/images/transform');
    routes.push('POST   /api/v1/renders/meme');
  }
  console.log('AVAILABLE_ROUTES');
  routes.sort().forEach(r => console.log(r));
}

app.listen(PORT, () => {
  console.log(`persona-image-kit listening on :${PORT}`);
  printRoutes();
  console.log('READY');
});

export default app;