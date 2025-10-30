export const links = new Map(); // chatId → { accountId, lastSeen, meta? }

export function linkChat(chatId, accountId) {
  links.set(chatId, { accountId, lastSeen: Date.now() });
  return links.get(chatId);
}

export function getLink(chatId) {
  return links.get(chatId) || null;
}