import axios from 'axios';
import { nanoid } from 'nanoid';

function getToken() { return process.env.TELEGRAM_BOT_TOKEN || null; }
export function active() { return !!getToken(); }

export async function sendTelegram({ to, message }) {
  const token = getToken();
  if (!token) return { ok: false, error: 'telegram_disabled' };
  const id = nanoid();
  try {
    const url = `https://api.telegram.org/bot${token}/sendMessage`;
    const res = await axios.post(url, {
      chat_id: String(to),
      text: String(message)
    }, { headers: { 'Content-Type': 'application/json' } });
    return { ok: true, id, adapter: 'telegram', data: res.data };
  } catch (e) {
    return { ok: false, error: e?.message || 'telegram_send_failed' };
  }
}