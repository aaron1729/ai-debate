import { Redis } from '@upstash/redis';
import crypto from 'crypto';
import type { DebateProgressUpdate, DebateResult, ModelKey } from './debate-engine';

declare global {
  // eslint-disable-next-line no-var
  var __PROMPT_LOG_REDIS__: Redis | undefined;
}

const PROMPT_LOG_INDEX_KEY = 'promptlog:index';
const PROMPT_LOG_SIZE_KEY = 'promptlog:sizes';
const PROMPT_LOG_TOTAL_BYTES_KEY = 'promptlog:total_bytes';
const DEFAULT_MAX_BYTES = 214 * 1024 * 1024; // ~204 MiB headroom under free-tier 256 MiB cap
const DEFAULT_ENTRY_BYTES = 12_000;
const DEFAULT_TRIM_PROBABILITY = 0.1;

export interface DebateLogMetadata {
  id: string;
  claim: string;
  turns: number;
  proModel: ModelKey;
  conModel: ModelKey;
  judgeModel: ModelKey;
  firstSpeaker: 'pro' | 'con';
  usingServerKeys: boolean;
  userApiKeyProviders: string[];
  createdAt: string;
  ipHash?: string;
  userAgent?: string;
  durationMs?: number;
}

export interface DebateLogPayload {
  metadata: DebateLogMetadata;
  requestBody: unknown;
  updates?: DebateProgressUpdate[];
  result?: DebateResult;
  error?: {
    message: string;
    stack?: string;
    label?: string;
    statusCode?: number;
  };
}

function getRedisClient(): Redis | null {
  if (!(process.env.UPSTASH_REDIS_REST_URL && process.env.UPSTASH_REDIS_REST_TOKEN)) {
    return null;
  }

  if (global.__PROMPT_LOG_REDIS__) {
    return global.__PROMPT_LOG_REDIS__;
  }

  const client = Redis.fromEnv();
  global.__PROMPT_LOG_REDIS__ = client;
  return client;
}

function parseNumberEnv(value: string | undefined, fallback: number): number {
  if (!value) return fallback;
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

async function enforceMemoryCap(redis: Redis, currentBytes?: number): Promise<void> {
  const maxBytes = parseNumberEnv(process.env.PROMPT_LOG_MAX_BYTES, DEFAULT_MAX_BYTES);
  if (!Number.isFinite(maxBytes) || maxBytes <= 0) {
    return;
  }

  const trimProbability = parseNumberEnv(process.env.PROMPT_LOG_TRIM_PROBABILITY, DEFAULT_TRIM_PROBABILITY);
  if (trimProbability < 1 && Math.random() > trimProbability) {
    return;
  }

  try {
    let usedBytes: number | undefined = typeof currentBytes === 'number' ? currentBytes : undefined;
    if (usedBytes === undefined) {
      const stored = await redis.get(PROMPT_LOG_TOTAL_BYTES_KEY);
      usedBytes = stored ? Number(stored) : 0;
    }

    if (!Number.isFinite(usedBytes) || usedBytes <= maxBytes) {
      return;
    }

    const approxEntryBytes = parseNumberEnv(process.env.PROMPT_LOG_ENTRY_BYTES, DEFAULT_ENTRY_BYTES);

    while (usedBytes > maxBytes) {
      const entriesToTrim = Math.max(1, Math.ceil((usedBytes - maxBytes) / Math.max(approxEntryBytes, 1)));
      const keys = await redis.zrange<string[]>(PROMPT_LOG_INDEX_KEY, 0, entriesToTrim - 1);
      if (!keys.length) return;

      const sizeValuesRaw = await redis.hmget(PROMPT_LOG_SIZE_KEY, ...keys);
      const sizeValues = Array.isArray(sizeValuesRaw) ? sizeValuesRaw : [];
      let trimmedBytes = 0;
      sizeValues.forEach((value: unknown) => {
        const parsed = value ? Number(value) : 0;
        if (Number.isFinite(parsed) && parsed > 0) {
          trimmedBytes += parsed;
        }
      });

      const pipeline = redis.pipeline();
      pipeline.zrem(PROMPT_LOG_INDEX_KEY, ...keys);
      pipeline.hdel(PROMPT_LOG_SIZE_KEY, ...keys);
      keys.forEach((key) => pipeline.del(key));
      await pipeline.exec();

      if (trimmedBytes > 0) {
        await redis.decrby(PROMPT_LOG_TOTAL_BYTES_KEY, trimmedBytes);
        usedBytes -= trimmedBytes;
      } else {
        // Avoid infinite loops if size metadata is missing
        break;
      }
    }
  } catch (error) {
    console.warn('Prompt log retention check failed:', error);
  }
}

export function hashIp(input: string | null | undefined): string | undefined {
  const value = input?.trim();
  if (!value || value === 'unknown') return undefined;

  const salt = process.env.PROMPT_LOG_IP_SALT || process.env.IP_HASH_SALT || '';
  return crypto.createHash('sha256').update(`${salt}:${value}`).digest('hex');
}

export async function logDebateEntry(payload: DebateLogPayload): Promise<void> {
  const redis = getRedisClient();
  if (!redis) return;

  const key = `promptlog:${payload.metadata.createdAt}:${payload.metadata.id}`;
  const score = Date.parse(payload.metadata.createdAt) || Date.now();
  const serialized = JSON.stringify(payload);
  const entryBytes = Buffer.byteLength(serialized, 'utf8');

  try {
    const pipeline = redis.pipeline();
    pipeline.set(key, serialized);
    pipeline.zadd(PROMPT_LOG_INDEX_KEY, { score, member: key });
    pipeline.hset(PROMPT_LOG_SIZE_KEY, { [key]: entryBytes });
    await pipeline.exec();
  } catch (error) {
    console.warn('Prompt log write failed:', error);
    return;
  }

  let totalBytes: number | undefined;
  try {
    totalBytes = await redis.incrby(PROMPT_LOG_TOTAL_BYTES_KEY, entryBytes);
  } catch (error) {
    console.warn('Prompt log size tracking failed:', error);
  }

  await enforceMemoryCap(redis, totalBytes);
}
