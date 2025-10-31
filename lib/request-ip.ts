import { NextApiRequest } from 'next';

function stripPort(ip: string): string {
  if (!ip) return ip;

  // Remove IPv6 localhost prefix (::ffff:)
  let normalized = ip.startsWith('::ffff:') ? ip.slice(7) : ip;

  if ((normalized.match(/:/g) || []).length > 1) {
    if (normalized === '::1') {
      return '127.0.0.1';
    }
    return normalized;
  }

  if (normalized === 'localhost') {
    return '127.0.0.1';
  }

  // If IPv4 with port (e.g., 127.0.0.1:1234), strip the port
  const parts = normalized.split(':');
  if (parts.length === 2 && /^[0-9.]+$/.test(parts[0])) {
    return parts[0];
  }

  return normalized;
}

export function getClientIp(req: NextApiRequest): string {
  const forwarded = req.headers['x-forwarded-for'];
  let ip: string | undefined;

  if (typeof forwarded === 'string' && forwarded.length > 0) {
    ip = forwarded.split(',')[0]?.trim();
  } else if (Array.isArray(forwarded) && forwarded.length > 0) {
    ip = forwarded[0]?.trim();
  }

  if (!ip || ip.length === 0) {
    ip = req.socket?.remoteAddress || '';
  }

  ip = stripPort(ip);
  return ip && ip.length > 0 ? ip : 'unknown';
}

export function isLocalhostIp(ip: string): boolean {
  const normalized = stripPort(ip);
  return normalized === '127.0.0.1' || normalized === '::1' || normalized === 'localhost';
}
