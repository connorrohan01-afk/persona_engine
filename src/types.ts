export type Persona = { 
  id: string; 
  name: string; 
  traits: string[]; 
  refs?: string[] 
};

export type GenRequest = { 
  persona_id: string; 
  style: string; 
  count: number; 
  slots?: Record<string, any>; 
  tone?: string; 
  seed?: number 
};

export type GenResult = { 
  job_id: string; 
  images: { url: string; seed: number }[]; 
  metrics: Record<string, any> 
};

export type NotifyPayload = { 
  job_id: string; 
  persona_id: string; 
  style: string; 
  images: { url: string; seed: number }[]; 
  status: "ok"|"error"; 
  signature?: string 
};