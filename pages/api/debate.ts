import { NextApiRequest, NextApiResponse } from 'next';
import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';
import { runDebate, ModelKey, APIKeys, MODELS } from '../../lib/debate-engine';

// Rate limiter: 5 requests per 24 hours per IP per model
const redis = process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN
  ? Redis.fromEnv()
  : null;

const createRateLimiter = () => redis ? new Ratelimit({
  redis,
  limiter: Ratelimit.slidingWindow(5, '24 h'),
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

      // Get unique models used in this debate
      const modelsUsed = new Set([proModel, conModel, judgeModel]);
      const modelLimits: Record<string, any> = {};

      // Check rate limit for each model
      for (const modelKey of modelsUsed) {
        const ratelimit = createRateLimiter();
        if (ratelimit) {
          const modelIdentifier = `${identifier}:${modelKey}`;
          const result = await ratelimit.limit(modelIdentifier);
          modelLimits[modelKey] = result;

          if (!result.success) {
            // Return which model(s) are rate limited
            return res.status(429).json({
              error: 'Rate limit exceeded',
              message: `You have used your 5 free uses for ${MODELS[modelKey as ModelKey].name}. Please provide your own API keys to continue.`,
              model: modelKey,
              resetAt: new Date(result.reset * 1000).toISOString()
            });
          }
        }
      }

      // Return rate limit info for all models in headers
      res.setHeader('X-RateLimit-Models', JSON.stringify(
        Object.fromEntries(
          Object.entries(modelLimits).map(([model, data]) => [
            model,
            { remaining: data.remaining, reset: data.reset }
          ])
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
