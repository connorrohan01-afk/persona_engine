export function requireBearer(req, res, next) {
  const header = req.headers['authorization'] || '';
  const token = header.startsWith('Bearer ') ? header.slice(7) : null;
  const allow = process.env.AUTH_BEARER_TOKEN || 'router_token_123';
  if (!token || token !== allow) {
    return res.status(401).json({ ok: false, error: { message: 'unauthorized' } });
  }
  req.user = { ok: true, role: 'router' };
  next();
}