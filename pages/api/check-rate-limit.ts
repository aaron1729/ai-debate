import { NextApiRequest, NextApiResponse } from 'next';
import { Redis } from '@upstash/redis';
import { MODELS, ModelKey } from '../../lib/debate-engine';
import { getClientIp, isLocalhostIp } from '../../lib/request-ip';
import {
  ADMIN_RATE_LIMIT,
  NON_ADMIN_RATE_LIMIT,
  GLOBAL_MODEL_LIMIT
} from '../../lib/rate-limits';

const redis = process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN
  ? Redis.fromEnv()
  : null;

// TEMPORARY DEBUGGING LOGGING
// console.log('[check-rate-limit] env', {
//   url: process.env.UPSTASH_REDIS_REST_URL?.slice(0, 40), // mask token in logs
//   tokenPresent: Boolean(process.env.UPSTASH_REDIS_REST_TOKEN)
// });
///////////////

const ADMIN_IP = process.env.ADMIN_IP;

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  res.setHeader('Cache-Control', 'no-store, max-age=0, must-revalidate');
  res.setHeader('Pragma', 'no-cache');
  res.setHeader('Expires', '0');
  res.removeHeader('ETag');

  const identifier = getClientIp(req);
  const isLocalhost = isLocalhostIp(identifier);
  const isAdmin = Boolean(ADMIN_IP && (identifier === ADMIN_IP || isLocalhost));
  const rateLimit = isAdmin ? ADMIN_RATE_LIMIT : NON_ADMIN_RATE_LIMIT;

  // Check actual usage from Redis for all models without consuming tokens
  const modelKeys = Object.keys(MODELS) as ModelKey[];
  const modelLimits: Record<string, any> = {};

  if (redis) {
    // Build pipeline with all Redis commands in a single batch
    console.log('[check-rate-limit] Using Redis pipelining for batched requests');
    const pipelineStart = Date.now();
    const pipeline = redis.pipeline();
    const keyMapping: Array<{ modelKey: ModelKey; usageKey: string; slidingKey: string; globalUsageKey: string; globalSlidingKey: string }> = [];

    for (const modelKey of modelKeys) {
      const modelIdentifier = `${identifier}:${modelKey}`;
      const usageKey = `ratelimit:usage:${modelIdentifier}`;
      const slidingKey = `@upstash/ratelimit:${modelIdentifier}`;
      const globalUsageKey = `ratelimit:usage-global:${modelKey}`;
      const globalSlidingKey = `@upstash/ratelimit:global:${modelKey}`;

      // Queue all 4 commands for this model
      pipeline.get(usageKey);
      pipeline.zcard(slidingKey);
      pipeline.zcard(globalSlidingKey);
      pipeline.get(globalUsageKey);

      keyMapping.push({ modelKey, usageKey, slidingKey, globalUsageKey, globalSlidingKey });
    }

    // Execute all commands in a single round-trip
    try {
      console.log('[check-rate-limit] Executing pipeline with', modelKeys.length * 4, 'commands');
      const execStart = Date.now();
      const results = await pipeline.exec();
      const execEnd = Date.now();
      console.log('[check-rate-limit] Pipeline executed in', execEnd - execStart, 'ms');

      // Process results (results array has 4 entries per model)
      for (let i = 0; i < modelKeys.length; i++) {
        const { modelKey, slidingKey, globalSlidingKey } = keyMapping[i];
        const baseIdx = i * 4;

        let storedUsed: number | null = null;
        let reset: number | null = null;
        let globalStoredUsed: number | null = null;
        let globalReset: number | null = null;
        let slidingEntries = 0;
        let globalSlidingEntries = 0;

        // Parse usageKey result
        try {
          const usedRaw = results[baseIdx];
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
          // ignore
        }

        // Parse slidingKey result
        try {
          const result = results[baseIdx + 1];
          const sanitized = Number(result);
          if (!Number.isNaN(sanitized)) {
            slidingEntries = sanitized;
          }
        } catch (err) {
          // ignore
        }

        // Parse globalSlidingKey result
        try {
          const globalResult = results[baseIdx + 2];
          const sanitized = Number(globalResult);
          if (!Number.isNaN(sanitized)) {
            globalSlidingEntries = sanitized;
          }
        } catch (err) {
          // ignore
        }

        // Parse globalUsageKey result
        try {
          const globalRaw = results[baseIdx + 3];
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
          // ignore
        }

        const effectiveUsed = storedUsed !== null ? storedUsed : slidingEntries;
        const effectiveGlobalUsed = globalStoredUsed !== null ? globalStoredUsed : globalSlidingEntries;

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
    } catch (err) {
      console.error('Pipeline execution failed:', err);
      // Fallback: return default limits for all models
      for (const modelKey of modelKeys) {
        modelLimits[modelKey] = {
          remaining: rateLimit,
          limit: rateLimit,
          reset: null,
          globalRemaining: GLOBAL_MODEL_LIMIT,
          globalLimit: GLOBAL_MODEL_LIMIT,
          globalReset: null,
          slidingKey: '',
          globalSlidingKey: '',
          slidingEntries: 0,
          globalSlidingEntries: 0
        };
      }
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
