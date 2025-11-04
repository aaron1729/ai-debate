const parseRateLimit = (value: string | undefined, fallback: number): number => {
  if (!value) return fallback;
  const parsed = parseInt(value, 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
};

const adminEnv = process.env.ADMIN_RATE_LIMIT;
const nonAdminEnv =
  process.env.NON_ADMIN_RATE_LIMIT ??
  process.env.RATE_LIMIT; // allow either env var name

export const ADMIN_RATE_LIMIT = parseRateLimit(adminEnv, 500);
export const NON_ADMIN_RATE_LIMIT = parseRateLimit(nonAdminEnv, 5);
export const GLOBAL_MODEL_LIMIT = parseRateLimit(process.env.GLOBAL_MODEL_LIMIT, 200);
