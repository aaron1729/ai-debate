import { NextApiRequest, NextApiResponse } from 'next';
import { Redis } from '@upstash/redis';
import { MODELS, ModelKey } from '../../lib/debate-engine';
import { getClientIp, isLocalhostIp } from '../../lib/request-ip';

const redis = process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN
  ? Redis.fromEnv()
  : null;




// TEMPORARY DEBUGGING LOGGING
console.log('[check-rate-limit] env', {
  url: process.env.UPSTASH_REDIS_REST_URL?.slice(0, 40), // mask token in logs
  tokenPresent: Boolean(process.env.UPSTASH_REDIS_REST_TOKEN)
});
///////////////


const ADMIN_IP = process.env.ADMIN_IP;
const ADMIN_RATE_LIMIT = parseInt(process.env.ADMIN_RATE_LIMIT || '500', 10);
const DEFAULT_RATE_LIMIT = 5;
const GLOBAL_MODEL_LIMIT = parseInt(process.env.GLOBAL_MODEL_LIMIT || '200', 10);

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const identifier = getClientIp(req);
  const isLocalhost = isLocalhostIp(identifier);
  const isAdmin = Boolean(ADMIN_IP && (identifier === ADMIN_IP || isLocalhost));
  const rateLimit = isAdmin ? ADMIN_RATE_LIMIT : DEFAULT_RATE_LIMIT;

  // Check actual usage from Redis for all models without consuming tokens
  const modelKeys = Object.keys(MODELS) as ModelKey[];
  const modelLimits: Record<string, any> = {};

  if (redis) {
    for (const modelKey of modelKeys) {
      const modelIdentifier = `${identifier}:${modelKey}`;
      const usageKey = `ratelimit:usage:${modelIdentifier}`;
      const slidingKey = `@upstash/ratelimit:${modelIdentifier}`;
      const globalUsageKey = `ratelimit:usage-global:${modelKey}`;
      const globalSlidingKey = `@upstash/ratelimit:global:${modelKey}`;


      // TEMPORARY DEBUGGING LOGGING
    const usageRaw = redis ? await redis.get(usageKey) : null;
    console.log('[check-rate-limit] raw snapshot', usageKey, usageRaw);
    ///////////////

      let storedUsed: number | null = null;
      let reset: number | null = null;
      let globalStoredUsed: number | null = null;
      let globalReset: number | null = null;
      let slidingEntries = 0;
      let globalSlidingEntries = 0;

      try {
        const usedRaw = await redis.get(usageKey);
        if (usedRaw) {
          if (typeof usedRaw === 'string') {
            const parsed = JSON.parse(usedRaw);
            storedUsed = typeof parsed.used === 'number' ? parsed.used : Number(parsed.used) || 0;
            reset = typeof parsed.reset === 'number' ? parsed.reset : parsed.reset ? Number(parsed.reset) : null;
          } else if (typeof usedRaw === 'number') {
            storedUsed = usedRaw;
          } else if (typeof usedRaw === 'object') {
            const parsed = usedRaw as any;
            storedUsed = typeof parsed.used === 'number' ? parsed.used : Number(parsed.used) || 0;
            reset = typeof parsed.reset === 'number' ? parsed.reset : parsed.reset ? Number(parsed.reset) : null;
          }
        }
      } catch (err) {
        storedUsed = null;
        reset = null;
      }

      try {
        const result = await redis.zcard(slidingKey);
        const sanitized = Number(result);
        if (!Number.isNaN(sanitized)) {
          slidingEntries = sanitized;
        }
      } catch (err) {
        // ignore
      }

      try {
        const globalResult = await redis.zcard(globalSlidingKey);
        const sanitized = Number(globalResult);
        if (!Number.isNaN(sanitized)) {
          globalSlidingEntries = sanitized;
        }
      } catch (err) {
        // ignore
      }

      try {
        const globalRaw = await redis.get(globalUsageKey);
        if (globalRaw) {
          if (typeof globalRaw === 'string') {
            const parsed = JSON.parse(globalRaw);
            globalStoredUsed = typeof parsed.used === 'number' ? parsed.used : Number(parsed.used) || 0;
            globalReset = typeof parsed.reset === 'number' ? parsed.reset : parsed.reset ? Number(parsed.reset) : null;
          } else if (typeof globalRaw === 'number') {
            globalStoredUsed = globalRaw;
          } else if (typeof globalRaw === 'object') {
            const parsed = globalRaw as any;
            globalStoredUsed = typeof parsed.used === 'number' ? parsed.used : Number(parsed.used) || 0;
            globalReset = typeof parsed.reset === 'number' ? parsed.reset : parsed.reset ? Number(parsed.reset) : null;
          }
        }
      } catch (err) {
        globalStoredUsed = null;
        globalReset = null;
      }

      const effectiveUsed = storedUsed !== null ? storedUsed : slidingEntries;
      const effectiveGlobalUsed = globalStoredUsed !== null ? globalStoredUsed : globalSlidingEntries;

      console.log('[check-rate-limit]', {
        usageKey,
        storedUsed,
        slidingEntries,
        effectiveUsed,
        globalUsageKey,
        globalStoredUsed,
        globalSlidingEntries,
        effectiveGlobalUsed
      });

      const actualRemaining = Math.max(0, rateLimit - effectiveUsed);
      const globalRemaining = Math.max(0, GLOBAL_MODEL_LIMIT - effectiveGlobalUsed);

      modelLimits[modelKey] = {
        remaining: actualRemaining,
        limit: rateLimit,
        reset,
        globalRemaining,
        globalLimit: GLOBAL_MODEL_LIMIT,
        globalReset,
        slidingKey,
        globalSlidingKey,
        slidingEntries,
        globalSlidingEntries
      };
    }
  }

  if (!redis) {
    modelKeys.forEach(modelKey => {
      modelLimits[modelKey] = {
        remaining: rateLimit,
        limit: rateLimit,
        reset: null,
        globalRemaining: GLOBAL_MODEL_LIMIT,
        globalLimit: GLOBAL_MODEL_LIMIT,
        globalReset: null
      };
    });
  }

  return res.status(200).json({
    limit: rateLimit,
    isAdmin,
    globalLimit: GLOBAL_MODEL_LIMIT,
    modelLimits
  });
}
