import { NextApiRequest, NextApiResponse } from 'next';
import { Redis } from '@upstash/redis';
import { MODELS, ModelKey } from '../../lib/debate-engine';

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
    return res.status(200).json({ error: 'Redis not configured', limits: {} });
  }

  const ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress || 'unknown';
  const identifier = Array.isArray(ip) ? ip[0] : ip;

  // Determine rate limit based on IP
  const isLocalhost = identifier === '::1' || identifier === '127.0.0.1' || identifier === '::ffff:127.0.0.1';
  const isAdmin = ADMIN_IP && (identifier === ADMIN_IP || isLocalhost);
  const rateLimit = isAdmin ? ADMIN_RATE_LIMIT : DEFAULT_RATE_LIMIT;

  // Check all models
  const modelKeys = Object.keys(MODELS) as ModelKey[];
  const usage: Record<string, any> = {};

  for (const modelKey of modelKeys) {
    const modelIdentifier = `${identifier}:${modelKey}`;

    // Try to get the current count from Redis
    // Upstash Ratelimit uses keys in the format: @upstash/ratelimit:{identifier}
    const redisKey = `@upstash/ratelimit:${modelIdentifier}`;

    try {
      const data = await redis.get(redisKey);
      usage[modelKey] = {
        redisKey,
        data,
        identifier: modelIdentifier
      };
    } catch (err) {
      usage[modelKey] = { error: String(err) };
    }
  }

  return res.status(200).json({
    ip: identifier,
    isAdmin,
    rateLimit,
    usage
  });
}
