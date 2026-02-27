import { NextApiRequest, NextApiResponse } from 'next';
import { Redis } from '@upstash/redis';

const redis = process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN
  ? Redis.fromEnv()
  : null;

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  // Verify this is called by Vercel Cron (or an authorized caller)
  const authHeader = req.headers['authorization'];
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return res.status(401).json({ error: 'Unauthorized' });
  }

  if (!redis) {
    return res.status(500).json({ error: 'Redis not configured' });
  }

  const timestamp = new Date().toISOString();
  await redis.set('keepalive:last_ping', timestamp);

  console.log(`[keep-alive] Pinged Redis at ${timestamp}`);
  return res.status(200).json({ ok: true, timestamp });
}
