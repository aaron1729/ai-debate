import { NextApiRequest, NextApiResponse } from 'next';
import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';
import { runDebate, ModelKey, APIKeys, MODELS } from '../../lib/debate-engine';

// Rate limiter: 5 requests per 24 hours per IP per model (500 for admin)
const redis = process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN
  ? Redis.fromEnv()
  : null;

const ADMIN_IP = process.env.ADMIN_IP;
const ADMIN_RATE_LIMIT = parseInt(process.env.ADMIN_RATE_LIMIT || '500', 10);
const DEFAULT_RATE_LIMIT = 5;

// Use admin rate limit as the max for tracking, then check against user's actual limit
const ratelimiter = redis ? new Ratelimit({
  redis,
  limiter: Ratelimit.slidingWindow(ADMIN_RATE_LIMIT, '24 h'),
  analytics: true,
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
      const ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress || 'unknown';
      const identifier = Array.isArray(ip) ? ip[0] : ip;

      // Determine rate limit based on IP
      // For localhost (::1, 127.0.0.1, ::ffff:127.0.0.1), treat as admin if ADMIN_IP is set
      const isLocalhost = identifier === '::1' || identifier === '127.0.0.1' || identifier === '::ffff:127.0.0.1';
      const isAdmin = ADMIN_IP && (identifier === ADMIN_IP || isLocalhost);
      const rateLimit = isAdmin ? ADMIN_RATE_LIMIT : DEFAULT_RATE_LIMIT;

      // Debug logging
      console.log(`[Rate Limit] IP: ${identifier}, isLocalhost: ${isLocalhost}, isAdmin: ${isAdmin}, limit: ${rateLimit}`);

      // Get unique models used in this debate
      const modelsUsed = Array.from(new Set([proModel, conModel, judgeModel]));
      const modelLimits: Record<string, any> = {};

      // Check rate limit for each model
      for (const modelKey of modelsUsed) {
        if (ratelimiter) {
          const modelIdentifier = `${identifier}:${modelKey}`;
          const result = await ratelimiter.limit(modelIdentifier);
          modelLimits[modelKey] = result;

          // Check if user has exceeded THEIR limit (not the admin limit)
          const used = ADMIN_RATE_LIMIT - result.remaining;
          if (used >= rateLimit) {
            // Return which model(s) are rate limited
            return res.status(429).json({
              error: 'Rate limit exceeded',
              message: `You have used your ${rateLimit} free uses for ${MODELS[modelKey as ModelKey].name}. Please provide your own API keys to continue.`,
              model: modelKey,
              resetAt: new Date(result.reset * 1000).toISOString(),
              remaining: Math.max(0, rateLimit - used)
            });
          }
        }
      }

      // Return rate limit info for all models in headers
      res.setHeader('X-RateLimit-Models', JSON.stringify(
        Object.fromEntries(
          Object.entries(modelLimits).map(([model, data]) => {
            const used = ADMIN_RATE_LIMIT - data.remaining;
            const actualRemaining = Math.max(0, rateLimit - used);
            return [
              model,
              { remaining: actualRemaining, reset: data.reset, limit: rateLimit }
            ];
          })
        )
      ));
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
