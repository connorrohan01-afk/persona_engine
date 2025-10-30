import { Router } from 'express';
import { parse,ClusterCreateSchema,ClusterPatchSchema } from '../lib/validators.js';
import { createCluster,listClusters,getCluster,patchCluster,deleteCluster } from '../lib/store.js';

const r=Router();

r.post('/',(req,res)=>{
  const v=parse(ClusterCreateSchema,req.body||{});
  if(!v.ok) return res.status(400).json({ok:false,error:v.error});
  const c=createCluster(v.data);
  console.log("[CLUSTER] created",c.id);
  res.json({ok:true,data:c});
});

r.get('/',(_req,res)=>res.json({ok:true,data:listClusters()}));

r.get('/:id',(req,res)=>{
  const c=getCluster(req.params.id);
  if(!c) return res.status(404).json({ok:false,error:{message:"not_found"}});
  res.json({ok:true,data:c});
});

r.patch('/:id',(req,res)=>{
  const v=parse(ClusterPatchSchema,req.body||{});
  if(!v.ok) return res.status(400).json({ok:false,error:v.error});
  const c=patchCluster(req.params.id,v.data);
  if(!c) return res.status(404).json({ok:false,error:{message:"not_found"}});
  res.json({ok:true,data:c});
});

r.delete('/:id',(req,res)=>{
  const ok=deleteCluster(req.params.id);
  if(!ok) return res.status(404).json({ok:false,error:{message:"not_found"}});
  res.json({ok:true,data:{id:req.params.id,deleted:true}});
});

// Activate
r.post('/:id/activate',(req,res)=>{
  const c=getCluster(req.params.id);
  if(!c) return res.status(404).json({ok:false,error:{message:"not_found"}});
  const upd=patchCluster(req.params.id,{status:"active"});
  res.json({ok:true,data:upd});
});

// Pause
r.post('/:id/pause',(req,res)=>{
  const c=getCluster(req.params.id);
  if(!c) return res.status(404).json({ok:false,error:{message:"not_found"}});
  const upd=patchCluster(req.params.id,{status:"paused"});
  res.json({ok:true,data:upd});
});

// Sync (stub)
r.post('/:id/sync',(req,res)=>{
  const c=getCluster(req.params.id);
  if(!c) return res.status(404).json({ok:false,error:{message:"not_found"}});
  res.json({ok:true,data:{id:c.id,sync:"ok"}});
});

export default r;