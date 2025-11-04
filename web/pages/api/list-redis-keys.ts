import { NextApiRequest, NextApiResponse } from 'next';
import { Redis } from '@upstash/redis';

const redis = process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN
  ? Redis.fromEnv()
  : null;

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  if (!redis) {
    return res.status(200).json({ error: 'Redis not configured' });
  }

  try {
    // Scan for all keys matching the ratelimit pattern
    const keys = await redis.keys('@upstash/ratelimit:*');

    // Get values for each key (they're sorted sets for sliding window)
    const keyValues: Record<string, any> = {};
    for (const key of keys) {
      try {
        // Try to get as sorted set
        const count = await redis.zcard(key);
        const members = await redis.zrange(key, 0, -1, { withScores: true });
        keyValues[key] = { count, members };
      } catch (err) {
        keyValues[key] = { error: String(err) };
      }
    }

    return res.status(200).json({
      count: keys.length,
      keys: keyValues
    });
  } catch (err) {
    return res.status(500).json({ error: String(err) });
  }
}
