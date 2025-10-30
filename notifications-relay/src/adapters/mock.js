import { nanoid } from 'nanoid';
export async function sendMock({ to, message, meta }) {
  const id = nanoid();
  console.log('[MOCK SEND]', id, { to, message, meta });
  return { ok: true, id, adapter: 'mock' };
}
export function active() { return true; }