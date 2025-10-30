const AUTH_BEARER_TOKEN = process.env.AUTH_BEARER_TOKEN || 'tg_router_token_123';

export async function call(serviceEnvName, path, { method = 'POST', json } = {}) {
  const base = process.env[serviceEnvName];
  if (!base) {
    return { ok: false, error: 'unconfigured' };
  }

  try {
    const headers = {
      'Authorization': `Bearer ${AUTH_BEARER_TOKEN}`
    };
    
    if (json) {
      headers['Content-Type'] = 'application/json';
    }

    const response = await fetch(base + path, {
      method,
      headers,
      body: json ? JSON.stringify(json) : undefined
    });

    const result = await response.json();
    return result;
  } catch (error) {
    return { ok: false, error: error.message };
  }
}

export function getContentUrl() {
  return process.env.CONTENT_URL;
}

export function getPosterUrl() {
  return process.env.POSTER_URL;
}

export function getSchedulerUrl() {
  return process.env.SCHEDULER_URL;
}

export function getIntakeUrl() {
  return process.env.INTAKE_URL;
}

export function getVaultsUrl() {
  return process.env.VAULTS_URL;
}