import { ModelKey, MODELS } from './debate-engine';

export interface SampleDebate {
  id: string;
  claim: string;
}

export interface ConfiguredSample extends SampleDebate {
  turns: number;
  proModel: ModelKey;
  conModel: ModelKey;
  judgeModel: ModelKey;
  openingSide: 'pro' | 'con';
}

export interface ModelLimitInfo {
  remaining?: number;
  globalRemaining?: number;
}

export type ModelLimits = Record<string, ModelLimitInfo>;

// 6 hardcoded sample debate claims
export const SAMPLE_CLAIMS: SampleDebate[] = [
  { id: '1', claim: 'A hot dog is a type of sandwich.' },
  { id: '2', claim: 'Humanity would be better off with a Universal Basic Income.' },
  { id: '3', claim: 'Free will is an illusion.' },
  { id: '4', claim: 'Mathematics is discovered, not invented.' },
  { id: '5', claim: 'Anti-Zionism is anti-Semitism.' },
  { id: '6', claim: 'Cereal is a type of soup.' },
];

interface DebateConfig {
  proModel: ModelKey;
  conModel: ModelKey;
  judgeModel: ModelKey;
  turns: number;
}

/**
 * Generate all 128 possible debate configurations
 * 4 models × 4 models × 4 models × 2 turn counts = 128 combinations
 */
function generateAllPossibleConfigs(): DebateConfig[] {
  const allModels = Object.keys(MODELS) as ModelKey[];
  const configs: DebateConfig[] = [];

  for (const proModel of allModels) {
    for (const conModel of allModels) {
      for (const judgeModel of allModels) {
        for (const turns of [1, 2]) {
          configs.push({ proModel, conModel, judgeModel, turns });
        }
      }
    }
  }

  return configs;
}

/**
 * Check if a specific config is valid given the available model limits
 * A config is valid if all required models have sufficient remaining uses
 */
function isConfigValid(
  config: DebateConfig,
  modelLimits: ModelLimits,
  rateLimit: number,
  globalLimit: number
): boolean {
  // Calculate required uses per model for this config
  const requiredUses: Record<string, number> = {};

  // Pro and con models each need 'turns' uses
  requiredUses[config.proModel] = (requiredUses[config.proModel] || 0) + config.turns;
  requiredUses[config.conModel] = (requiredUses[config.conModel] || 0) + config.turns;

  // Judge model needs 1 use
  requiredUses[config.judgeModel] = (requiredUses[config.judgeModel] || 0) + 1;

  // Check if all required models have sufficient uses
  for (const [model, usesNeeded] of Object.entries(requiredUses)) {
    const info = modelLimits[model];
    const remaining = info?.remaining ?? rateLimit;
    const globalRemaining = info?.globalRemaining ?? globalLimit;

    if (remaining < usesNeeded || globalRemaining < usesNeeded) {
      return false;
    }
  }

  return true;
}

/**
 * Get a random opening side
 */
function randomOpeningSide(): 'pro' | 'con' {
  return Math.random() < 0.5 ? 'pro' : 'con';
}

/**
 * Generate configured sample debates based on available model limits
 * Uses optimized pre-computation approach:
 * 1. Generate all 128 possible configs
 * 2. Filter to valid configs (have enough uses)
 * 3. If none valid, return empty array
 * 4. Otherwise, sample 6 configs WITH REPLACEMENT and assign to sample claims
 */
export function generateSampleConfigs(
  modelLimits: ModelLimits,
  rateLimit: number,
  globalLimit: number
): ConfiguredSample[] {
  const overallStart = performance.now();

  // Step 1: Generate all 128 possible configs
  const step1Start = performance.now();
  const allConfigs = generateAllPossibleConfigs();
  const step1End = performance.now();
  console.log('[generateSampleConfigs] Step 1 - Generated all configs', {
    count: allConfigs.length,
    elapsed: `${(step1End - step1Start).toFixed(2)}ms`
  });

  // Step 2: Filter to only valid configs
  const step2Start = performance.now();
  const validConfigs = allConfigs.filter(config =>
    isConfigValid(config, modelLimits, rateLimit, globalLimit)
  );
  const step2End = performance.now();
  console.log('[generateSampleConfigs] Step 2 - Filtered valid configs', {
    validCount: validConfigs.length,
    totalCount: allConfigs.length,
    elapsed: `${(step2End - step2Start).toFixed(2)}ms`
  });

  // Step 3: If no valid configs, return empty array (no cards shown)
  if (validConfigs.length === 0) {
    console.log('[generateSampleConfigs] No valid configs found, returning empty array');
    return [];
  }

  // Step 4: Sample 6 configs WITH REPLACEMENT from valid configs
  const step4Start = performance.now();
  const selectedConfigs: ConfiguredSample[] = [];

  for (let i = 0; i < SAMPLE_CLAIMS.length; i++) {
    // Random selection with replacement
    const randomConfig = validConfigs[Math.floor(Math.random() * validConfigs.length)];

    selectedConfigs.push({
      ...SAMPLE_CLAIMS[i],
      ...randomConfig,
      openingSide: randomOpeningSide(),
    });
  }
  const step4End = performance.now();
  console.log('[generateSampleConfigs] Step 4 - Sampled configs', {
    count: selectedConfigs.length,
    elapsed: `${(step4End - step4Start).toFixed(2)}ms`
  });

  const overallEnd = performance.now();
  console.log('[generateSampleConfigs] TOTAL', {
    elapsed: `${(overallEnd - overallStart).toFixed(2)}ms`
  });

  return selectedConfigs;
}
