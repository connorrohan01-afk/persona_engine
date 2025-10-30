import nodemailer from 'nodemailer';
import { nanoid } from 'nanoid';

let cached = null;
function getTransport() {
  if (cached) return cached;
  const host = process.env.SMTP_HOST;
  const port = Number(process.env.SMTP_PORT || 587);
  const user = process.env.SMTP_USER;
  const pass = process.env.SMTP_PASS;
  if (!host || !user || !pass) return null;
  cached = nodemailer.createTransport({
    host, port, secure: port === 465,
    auth: { user, pass }
  });
  return cached;
}

export function active() { return !!getTransport(); }

export async function sendEmail({ to, message }) {
  const t = getTransport();
  if (!t) return { ok: false, error: 'email_disabled' };
  const id = nanoid();
  const from = process.env.RELAY_FROM || 'Notifications <no-reply@example.com>';
  try {
    const info = await t.sendMail({
      from, to: String(to), subject: 'Notification', text: String(message)
    });
    return { ok: true, id, adapter: 'email', data: { messageId: info.messageId } };
  } catch (e) {
    return { ok: false, error: e?.message || 'email_send_failed' };
  }
}