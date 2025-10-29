import { NextApiRequest, NextApiResponse } from 'next';
import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';
import { MODELS, ModelKey } from '../../lib/debate-engine';

const redis = process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN
  ? Redis.fromEnv()
  : null;

const ADMIN_IP = process.env.ADMIN_IP;
const ADMIN_RATE_LIMIT = parseInt(process.env.ADMIN_RATE_LIMIT || '500', 10);
const DEFAULT_RATE_LIMIT = 5;

// Use same rate limiter as debate.ts
const ratelimiter = redis ? new Ratelimit({
  redis,
  limiter: Ratelimit.slidingWindow(ADMIN_RATE_LIMIT, '24 h'),
  analytics: true,
}) : null;

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress || 'unknown';
  const identifier = Array.isArray(ip) ? ip[0] : ip;

  // Determine rate limit based on IP
  // For localhost (::1, 127.0.0.1, ::ffff:127.0.0.1), treat as admin if ADMIN_IP is set
  const isLocalhost = identifier === '::1' || identifier === '127.0.0.1' || identifier === '::ffff:127.0.0.1';
  const isAdmin = ADMIN_IP && (identifier === ADMIN_IP || isLocalhost);
  const rateLimit = isAdmin ? ADMIN_RATE_LIMIT : DEFAULT_RATE_LIMIT;

  // Check actual usage from Redis for all models without consuming tokens
  const modelKeys = Object.keys(MODELS) as ModelKey[];
  const modelLimits: Record<string, { remaining: number; limit: number }> = {};

  if (redis && ratelimiter) {
    const now = Date.now();

    for (const modelKey of modelKeys) {
      const modelIdentifier = `${identifier}:${modelKey}`;

      try {
        // Use getRemaining to check without consuming
        // This uses the internal prefix that Upstash Ratelimit uses
        const script = `
          local key = KEYS[1]
          local window = tonumber(ARGV[1])
          local now = tonumber(ARGV[2])

          -- Remove old entries outside the window
          redis.call('zremrangebyscore', key, 0, now - window)

          -- Count remaining entries
          local count = redis.call('zcard', key)

          return count
        `;

        const windowMs = 24 * 60 * 60 * 1000; // 24 hours
        const redisKey = `@upstash/ratelimit:${modelIdentifier}`;

        const used = await redis.eval(
          script,
          [redisKey],
          [windowMs.toString(), now.toString()]
        ) as number || 0;

        const actualRemaining = Math.max(0, rateLimit - used);

        modelLimits[modelKey] = {
          remaining: actualRemaining,
          limit: rateLimit
        };
      } catch (err) {
        // If key doesn't exist or error, assume no usage
        modelLimits[modelKey] = {
          remaining: rateLimit,
          limit: rateLimit
        };
      }
    }
  }

  return res.status(200).json({
    limit: rateLimit,
    isAdmin,
    modelLimits
  });
}
