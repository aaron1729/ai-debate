import { NextApiRequest, NextApiResponse } from 'next';
import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';
import { MODELS, ModelKey } from '../../lib/debate-engine';
import { getClientIp, isLocalhostIp } from '../../lib/request-ip';

const redis = process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN
  ? Redis.fromEnv()
  : null;

const ADMIN_IP = process.env.ADMIN_IP;
const ADMIN_RATE_LIMIT = parseInt(process.env.ADMIN_RATE_LIMIT || '500', 10);
const DEFAULT_RATE_LIMIT = 5;

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

  const identifier = getClientIp(req);
  const isLocalhost = isLocalhostIp(identifier);
  const isAdmin = Boolean(ADMIN_IP && (identifier === ADMIN_IP || isLocalhost));
  const rateLimit = isAdmin ? ADMIN_RATE_LIMIT : DEFAULT_RATE_LIMIT;

  // Create rate limiter with the correct limit
  const rateLimiter = new Ratelimit({
    redis,
    limiter: Ratelimit.slidingWindow(rateLimit, '24 h'),
    analytics: true,
  });

  // Check all models using getRemaining (doesn't consume a token)
  const modelKeys = Object.keys(MODELS) as ModelKey[];
  const remaining: Record<string, any> = {};

  for (const modelKey of modelKeys) {
    const modelIdentifier = `${identifier}:${modelKey}`;

    try {
      // Use the limit function with DRY RUN mode by checking the result
      const result = await rateLimiter.limit(modelIdentifier, { rate: rateLimit });

      remaining[modelKey] = {
        limit: rateLimit,
        remaining: result.remaining,
        reset: result.reset,
        success: result.success
      };
    } catch (err) {
      remaining[modelKey] = { error: String(err) };
    }
  }

  return res.status(200).json({
    ip: identifier,
    isAdmin,
    rateLimit,
    remaining
  });
}
