import axios from 'axios';

export async function notifyStatusChange({ serviceId, prev, next, at, snapshot }) {
  const hook = process.env.WEBHOOK_URL; // optional
  if (!hook) return { sent: false, reason: 'no_webhook' };
  try {
    const res = await axios.post(hook, { serviceId, prev, next, at, snapshot }, {
      timeout: 5000,
      headers: { 'Content-Type': 'application/json' }
    });
    return { sent: true, code: res.status };
  } catch (e) {
    return { sent: false, error: e.message?.slice(0, 180) || 'error' };
  }
}