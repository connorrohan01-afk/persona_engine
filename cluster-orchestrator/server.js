import express from 'express';
import helmet from 'helmet';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';
import { bearerAuth } from './src/lib/auth.js';
import clustersRouter from './src/routes/clusters.js';
import healthRouter from './src/routes/health.js';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(helmet());
app.use(morgan('tiny'));
app.use(express.json({ limit: '1mb' }));

const limiter = rateLimit({ windowMs: 5 * 60 * 1000, max: 200, standardHeaders: true });
app.use(limiter);

app.use('/api/v1/health', healthRouter);
app.use('/api/v1/clusters', bearerAuth, clustersRouter);

app.use((req,res)=>res.status(404).json({ok:false,error:{message:"not_found"}}));

function printRoutes() {
  const routes=[];
  const scan=(stack,base="")=>{
    stack.forEach(l=>{
      if(l.route){
        const m=Object.keys(l.route.methods).map(x=>x.toUpperCase()).join(',');
        routes.push(`${m.padEnd(6)} ${base}${l.route.path}`);
      } else if(l.name==="router"&&l.handle?.stack){
        scan(l.handle.stack, base);
      }
    });
  };
  if (app._router && app._router.stack) {
    scan(app._router.stack);
  } else {
    // Fallback routes
    routes.push('GET    /api/v1/health');
    routes.push('GET    /api/v1/clusters');
    routes.push('POST   /api/v1/clusters');
    routes.push('GET    /api/v1/clusters/:id');
    routes.push('PATCH  /api/v1/clusters/:id');
    routes.push('DELETE /api/v1/clusters/:id');
    routes.push('POST   /api/v1/clusters/:id/activate');
    routes.push('POST   /api/v1/clusters/:id/pause');
    routes.push('POST   /api/v1/clusters/:id/sync');
  }
  console.log("AVAILABLE_ROUTES");
  routes.sort().forEach(r=>console.log(r));
}

app.listen(PORT,()=>{
  console.log(`cluster-orchestrator listening on :${PORT}`);
  printRoutes();
  console.log("READY: cluster-orchestrator");
});

export default app;