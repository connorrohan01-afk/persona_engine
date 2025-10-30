import { nanoid } from 'nanoid';
const clusters=new Map();

export function createCluster(payload){
  const id=nanoid();
  const now=new Date().toISOString();
  const c={id,createdAt:now,updatedAt:now,status:"draft",...payload};
  clusters.set(id,c);
  return c;
}
export function listClusters(){return Array.from(clusters.values());}
export function getCluster(id){return clusters.get(id)||null;}
export function patchCluster(id,patch){
  const cur=clusters.get(id);if(!cur) return null;
  const upd={...cur,...patch,updatedAt:new Date().toISOString()};
  clusters.set(id,upd);return upd;
}
export function deleteCluster(id){return clusters.delete(id);}