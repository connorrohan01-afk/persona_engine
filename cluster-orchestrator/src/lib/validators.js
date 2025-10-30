import { z } from 'zod';

export const ClusterCreateSchema=z.object({
  label:z.string().min(1),
  personaIds:z.array(z.string()).optional(),
  accountIds:z.array(z.string()).optional(),
  jobIds:z.array(z.string()).optional(),
  meta:z.record(z.any()).optional()
});

export const ClusterPatchSchema=z.object({
  label:z.string().optional(),
  personaIds:z.array(z.string()).optional(),
  accountIds:z.array(z.string()).optional(),
  jobIds:z.array(z.string()).optional(),
  status:z.enum(["draft","active","paused","archived"]).optional(),
  meta:z.record(z.any()).optional()
});

export function parse(schema,body){
  const r=schema.safeParse(body);
  if(!r.success) return {ok:false,error:r.error.flatten()};
  return {ok:true,data:r.data};
}