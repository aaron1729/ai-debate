import { NextApiRequest, NextApiResponse } from 'next';
import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';
import { runDebate, ModelKey, APIKeys, MODELS } from '../../lib/debate-engine';
import { getClientIp, isLocalhostIp } from '../../lib/request-ip';
import {
  ADMIN_RATE_LIMIT,
  NON_ADMIN_RATE_LIMIT,
  GLOBAL_MODEL_LIMIT
} from '../../lib/rate-limits';

// Rate limiter: per-model quotas (configurable via env / lib/rate-limits.ts)
const redis = process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN
  ? Redis.fromEnv()
  : null;

const ADMIN_IP = process.env.ADMIN_IP;

// Use admin rate limit as the max for tracking, then check against user's actual limit
const ratelimiter = redis ? new Ratelimit({
  redis,
  limiter: Ratelimit.slidingWindow(ADMIN_RATE_LIMIT, '24 h'),
  analytics: true,
}) : null;

const globalLimiter = redis ? new Ratelimit({
  redis,
  limiter: Ratelimit.slidingWindow(GLOBAL_MODEL_LIMIT, '24 h'),
  analytics: true,
  prefix: 'global-model-limit'
}) : null;

interface DebateRequest {
  claim: string;
  turns: number;
  proModel: ModelKey;
  conModel: ModelKey;
  judgeModel: ModelKey;
  userApiKeys?: APIKeys;
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { claim, turns, proModel, conModel, judgeModel, userApiKeys }: DebateRequest = req.body;

    // Validate input
    if (!claim || !proModel || !conModel || !judgeModel) {
      return res.status(400).json({ error: 'Missing required fields' });
    }

    if (turns < 1 || turns > 6) {
      return res.status(400).json({ error: 'Turns must be between 1 and 6' });
    }

    // Determine if using server keys or user keys
    const usingServerKeys = !userApiKeys || Object.keys(userApiKeys).length === 0;

    // If using server keys, apply per-model rate limiting
    if (usingServerKeys && redis) {
      const identifier = getClientIp(req);
      const isLocalhost = isLocalhostIp(identifier);
      const isAdmin = Boolean(ADMIN_IP && (identifier === ADMIN_IP || isLocalhost));
      const rateLimit = isAdmin ? ADMIN_RATE_LIMIT : NON_ADMIN_RATE_LIMIT;

      console.log(`[Rate Limit] IP: ${identifier}, isLocalhost: ${isLocalhost}, isAdmin: ${isAdmin}, limit: ${rateLimit}`);

      const usageCounts: Partial<Record<ModelKey, number>> = {};
      usageCounts[proModel] = (usageCounts[proModel] || 0) + turns;
      usageCounts[conModel] = (usageCounts[conModel] || 0) + turns;
      usageCounts[judgeModel] = (usageCounts[judgeModel] || 0) + 1;

      const perModelStatus: Record<string, { remaining: number; limit: number; reset: number | null }> = {};
      const globalStatus: Record<string, { remaining: number; limit: number; reset: number | null }> = {};

      for (const [modelKeyStr, count] of Object.entries(usageCounts)) {
        const modelKey = modelKeyStr as ModelKey;
        if (!count || count <= 0) continue;

        if (globalLimiter) {
          const globalIdentifier = `global:${modelKey}`;
          let globalResult;
          for (let i = 0; i < count; i++) {
            globalResult = await globalLimiter.limit(globalIdentifier);
            if (!globalResult.success) break;
          }

          if (globalResult) {
            const globalUsed = GLOBAL_MODEL_LIMIT - globalResult.remaining;
            const globalRemaining = Math.max(0, GLOBAL_MODEL_LIMIT - globalUsed);

            globalStatus[modelKey] = {
              remaining: globalRemaining,
              limit: GLOBAL_MODEL_LIMIT,
              reset: globalResult.reset ?? null
            };

            const globalUsageKey = `ratelimit:usage-global:${modelKey}`;
            await redis.set(globalUsageKey, JSON.stringify({
              used: globalUsed,
              reset: globalResult.reset ?? null
            }), { ex: 60 * 60 * 24 });

            if (!globalResult.success || globalRemaining <= 0) {
              return res.status(429).json({
                error: 'Rate limit exceeded',
                message: `The free tier usage for ${MODELS[modelKey].name} is exhausted. Provide your own API key or wait for the 24-hour window to reset.`,
                model: modelKey,
                type: 'global',
                resetAt: globalResult.reset ? new Date(globalResult.reset * 1000).toISOString() : null,
                remaining: 0
              });
            }
          }
        }

        if (ratelimiter) {
          const modelIdentifier = `${identifier}:${modelKey}`;
          let result;
          for (let i = 0; i < count; i++) {
            result = await ratelimiter.limit(modelIdentifier);
            if (!result.success) break;
          }

          if (result) {
            const used = ADMIN_RATE_LIMIT - result.remaining;
            const remaining = Math.max(0, rateLimit - used);

            perModelStatus[modelKey] = {
              remaining,
              limit: rateLimit,
              reset: result.reset ?? null
            };

            const usageKey = `ratelimit:usage:${modelIdentifier}`;
            await redis.set(usageKey, JSON.stringify({
              used,
              reset: result.reset ?? null
            }), { ex: 60 * 60 * 24 });

            if (used >= rateLimit || !result.success) {
              return res.status(429).json({
                error: 'Rate limit exceeded',
                message: `You have used your ${rateLimit} free uses for ${MODELS[modelKey].name}. Please provide your own API keys to continue.`,
                model: modelKey,
                type: 'per-user',
                resetAt: result.reset ? new Date(result.reset * 1000).toISOString() : null,
                remaining: Math.max(0, rateLimit - used)
              });
            }
          }
        }
      }

    }

    // Prepare API keys
    const apiKeys: APIKeys = usingServerKeys
      ? {
          anthropic: process.env.ANTHROPIC_API_KEY,
          openai: process.env.OPENAI_API_KEY,
          google: process.env.GOOGLE_API_KEY,
          xai: process.env.XAI_API_KEY,
        }
      : userApiKeys;

    // Run debate
    const result = await runDebate(
      claim,
      turns,
      proModel,
      conModel,
      judgeModel,
      apiKeys
    );

    return res.status(200).json(result);
  } catch (error: any) {
    console.error('Debate error:', error);

    // Handle specific error types
    if (error.message.includes('API_KEY')) {
      return res.status(400).json({
        error: 'Missing API key',
        message: error.message
      });
    }

    if (error.message.includes('API error')) {
      return res.status(502).json({
        error: 'API error',
        message: error.message
      });
    }

    return res.status(500).json({
      error: 'Internal server error',
      message: error.message
    });
  }
}
