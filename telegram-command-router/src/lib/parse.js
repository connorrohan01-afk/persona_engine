export function parseCommand(messageText, botUsername) {
  if (!messageText || typeof messageText !== 'string') return null;
  
  let text = messageText.trim();
  if (!text) return null;

  // Remove bot username if present (e.g., "/command@bot_name")
  if (botUsername && text.includes(`@${botUsername}`)) {
    text = text.replace(new RegExp(`@${botUsername}`, 'gi'), '');
  }

  // Extract command (with or without leading slash)
  const match = text.match(/^\/?([\w]+)(?:\s+(.*))?$/);
  if (!match) return null;

  const cmd = match[1].toLowerCase();
  const argsRaw = match[2] || '';
  
  // Split by :: first for complex commands
  const parts = argsRaw.split('::').map(p => p.trim()).filter(p => p);
  
  // For simple commands, split by spaces
  if (parts.length === 0) {
    const spaceParts = argsRaw.split(/\s+/).filter(p => p);
    parts.push(...spaceParts);
  }

  // Parse special command structures
  let kv = {};
  
  if (cmd === 'schedule' && argsRaw.includes('every')) {
    const schedMatch = argsRaw.match(/^(\w+)\s+every\s+(\d+)\s+(\w+)\s*::\s*(.+)$/i);
    if (schedMatch) {
      kv = {
        accountId: schedMatch[1],
        every: { value: parseInt(schedMatch[2]), unit: schedMatch[3] },
        remaining: schedMatch[4]
      };
    }
  }

  // Normalize subreddit (add r/ if missing)
  const normalizedParts = parts.map(part => {
    if (part.match(/^[a-zA-Z][a-zA-Z0-9_]+$/) && !part.startsWith('r/')) {
      return `r/${part}`;
    }
    return part;
  });

  return {
    cmd,
    argsRaw,
    parts: normalizedParts,
    kv: Object.keys(kv).length ? kv : undefined
  };
}