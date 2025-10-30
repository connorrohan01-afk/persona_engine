// Extremely simple, safe string interpolation and persona wrapping.
export function interpolate(body, variables = {}) {
  if (typeof body !== 'string') return '';
  return body.replace(/{{\s*([a-zA-Z0-9_.]+)\s*}}/g, (_m, key) => {
    const val = key.split('.').reduce((acc, k) => (acc && acc[k] != null ? acc[k] : undefined), variables);
    return (val === undefined || val === null) ? '' : String(val);
  });
}

export function applyPersona(text, persona) {
  if (!persona) return text;
  const v = persona.voice ? `[voice:${persona.voice}]` : '';
  const t = persona.tone ? `[tone:${persona.tone}]` : '';
  const rules = persona.rules && persona.rules.length ? `\n[rules:${persona.rules.join(' | ')}]` : '';
  return `${v}${t}${rules}\n${text}`;
}