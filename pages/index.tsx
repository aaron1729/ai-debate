import { useState, useEffect, useCallback } from 'react';
import Head from 'next/head';
import { MODELS, ModelKey, DebateResult, DebateTurn } from '../lib/debate-engine';
import messages from '../shared/messages.json';
import { generateSampleConfigs, ConfiguredSample } from '../lib/sample-debates';

type ModelLimitInfo = {
  remaining: number;
  limit?: number;
  reset?: number | null;
  globalRemaining?: number;
  globalLimit?: number;
  globalReset?: number | null;
};

export default function Home() {
  const [claim, setClaim] = useState('');
  const [turns, setTurns] = useState(2);
  const [firstSpeaker, setFirstSpeaker] = useState<'pro' | 'con'>('pro');
  const [proModel, setProModel] = useState<ModelKey>('claude');
  const [conModel, setConModel] = useState<ModelKey>('grok');
  const [judgeModel, setJudgeModel] = useState<ModelKey>('gpt4');
  const [loading, setLoading] = useState(false);
  type ProgressMessage = { primary: string; secondary?: string };
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState<ProgressMessage>({ primary: '', secondary: undefined });
  const [debateHistory, setDebateHistory] = useState<DebateTurn[]>([]);
  const [verdict, setVerdict] = useState<DebateResult['verdict'] | null>(null);
  const [error, setError] = useState<{
    userMessage: string;
    suggestion?: string;
    provider?: string;
    model?: string;
    category?: string;
    isRetryable?: boolean;
    completedSteps?: number;
  } | null>(null);
  const [showApiKeys, setShowApiKeys] = useState(false);
  const [apiKeys, setApiKeys] = useState({
    anthropic: '',
    openai: '',
    google: '',
    xai: ''
  });
  const [modelLimits, setModelLimits] = useState<Record<string, ModelLimitInfo>>({});
  const [hasLoadedLimits, setHasLoadedLimits] = useState(false);
  const [rateLimit, setRateLimit] = useState(5);
  const [globalLimit, setGlobalLimit] = useState(200);
  const [sampleDebates, setSampleDebates] = useState<ConfiguredSample[]>([]);

  const description = 'Adversarial Truth-Seeking Through Structured AI Debates';
  const rawSiteUrl = process.env.SITE_URL;
  const siteUrl = rawSiteUrl ? rawSiteUrl.replace(/\/$/, '') : '';
  const ogImagePath = '/og/og-ai-debate-B-circle-1200x630.png';
  const twitterImagePath = '/og/og-ai-debate-B-twitter-1200x628.png';
  const ogImageUrl = siteUrl ? `${siteUrl}${ogImagePath}` : ogImagePath;
  const twitterImageUrl = siteUrl ? `${siteUrl}${twitterImagePath}` : twitterImagePath;

  const modelKeys = Object.keys(MODELS) as ModelKey[];
  const trimmedKeysState = {
    anthropic: apiKeys.anthropic.trim(),
    openai: apiKeys.openai.trim(),
    google: apiKeys.google.trim(),
    xai: apiKeys.xai.trim()
  };
  const hasUserKeys = Object.values(trimmedKeysState).some(value => value.length > 0);
  const usingServerKeys = !(showApiKeys && hasUserKeys);

  const isModelExhausted = (model: ModelKey) => {
    const info = modelLimits[model];
    const remaining = info?.remaining ?? rateLimit;
    const globalRemaining = info?.globalRemaining ?? globalLimit;
    return remaining <= 0 || globalRemaining <= 0;
  };

  const allServerModelsExhausted = usingServerKeys && modelKeys.every(model => isModelExhausted(model));

  const fetchRateLimits = useCallback(async () => {
    const startTime = performance.now();
    console.log('[Rate Limits] Starting fetchRateLimits...', { startTime });

    try {
      const fetchStart = performance.now();
      const response = await fetch('/api/check-rate-limit', { cache: 'no-store' });
      const fetchEnd = performance.now();
      console.log('[Rate Limits] Fetch completed', { elapsed: `${(fetchEnd - fetchStart).toFixed(2)}ms` });

      if (!response.ok) {
        console.log('[Rate Limits] Response not OK', { status: response.status });
        return;
      }

      const parseStart = performance.now();
      const data = await response.json();
      const parseEnd = performance.now();
      console.log('[Rate Limits] JSON parsed', { elapsed: `${(parseEnd - parseStart).toFixed(2)}ms` });

      if (typeof data.limit === 'number') {
        setRateLimit(data.limit);
      }
      if (typeof data.globalLimit === 'number') {
        setGlobalLimit(data.globalLimit);
      }

      if (data.modelLimits) {
        setModelLimits(data.modelLimits);
        setHasLoadedLimits(true);
      }

      const endTime = performance.now();
      console.log('[Rate Limits] fetchRateLimits completed', {
        totalElapsed: `${(endTime - startTime).toFixed(2)}ms`,
        endTime
      });
    } catch (err) {
      console.error('Failed to check rate limit:', err);
    }
  }, []);

  // Fetch initial rate limit and usage on page load
  useEffect(() => {
    console.log('[Page Mount] Component mounted, page load started', { timestamp: Date.now() });
    fetchRateLimits();
  }, [fetchRateLimits]);

  // Generate sample debates when model limits are loaded or when a debate completes
  useEffect(() => {
    console.log('[Sample Debates] useEffect triggered', {
      modelLimitsKeys: Object.keys(modelLimits).length,
      loading,
      timestamp: Date.now()
    });

    // Only regenerate if modelLimits loaded AND not currently loading
    if (Object.keys(modelLimits).length > 0 && !loading) {
      const startTime = performance.now();
      console.log('[Sample Debates] Starting generateSampleConfigs...', { startTime });

      const newConfigs = generateSampleConfigs(modelLimits, rateLimit, globalLimit);

      const endTime = performance.now();
      const elapsed = endTime - startTime;
      console.log('[Sample Debates] generateSampleConfigs completed', {
        elapsed: `${elapsed.toFixed(2)}ms`,
        configsGenerated: newConfigs.length,
        endTime
      });

      setSampleDebates(newConfigs);
    }
  }, [modelLimits, loading, rateLimit, globalLimit]);

  const getVerdictColor = (verdictType: string) => {
    switch (verdictType) {
      case 'supported': return '#22c55e'; // green
      case 'contradicted': return '#ef4444'; // red
      case 'misleading': return '#f59e0b'; // orange
      case 'needs more evidence': return '#6b7280'; // gray
      default: return '#3b82f6'; // blue
    }
  };

  const handleSampleClick = (sample: ConfiguredSample) => {
    // Ignore if debate running
    if (loading) return;

    // Pre-fill form with sample debate configuration
    setClaim(sample.claim);
    setTurns(sample.turns);
    setProModel(sample.proModel);
    setConModel(sample.conModel);
    setJudgeModel(sample.judgeModel);
    setFirstSpeaker(sample.openingSide);

    // Trigger form submission (will be validated by handleSubmit)
    // We use setTimeout to ensure state updates have been applied
    setTimeout(() => {
      const form = document.querySelector('form');
      if (form) {
        form.requestSubmit();
      }
    }, 0);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setDebateHistory([]);
    setVerdict(null);
    setProgress(5);
    const proModelName = MODELS[proModel].name;
    const conModelName = MODELS[conModel].name;
    const judgeModelName = MODELS[judgeModel].name;
    const startMessageTemplate = messages.start.replace('{turns}', turns.toString());
    const singularStart = turns === 1
      ? startMessageTemplate.replace('turns per side', 'turn per side')
      : startMessageTemplate;
    const cleanedStart = singularStart.replace(/\.\.\.$/, '.');
    const startingSideLabel = firstSpeaker === 'pro' ? 'Pro' : 'Con';
    const startingModelName = firstSpeaker === 'pro' ? proModelName : conModelName;

    setProgressMessage({
      primary: cleanedStart,
      secondary: `${startingSideLabel} side (${startingModelName}) now making an argument in turn 1/${Math.max(turns, 1)}...`
    });

    try {
      // Determine which API keys to send
      const trimmedKeys = trimmedKeysState;
      const hasProvidedKeys = showApiKeys && Object.values(trimmedKeys).some(value => value.length > 0);
      const userApiKeys = hasProvidedKeys ? {
        ...(trimmedKeys.anthropic && { anthropic: trimmedKeys.anthropic }),
        ...(trimmedKeys.openai && { openai: trimmedKeys.openai }),
        ...(trimmedKeys.google && { google: trimmedKeys.google }),
        ...(trimmedKeys.xai && { xai: trimmedKeys.xai })
      } : undefined;

      if (!userApiKeys) {
        const exhaustedSelection = [proModel, conModel, judgeModel].some(model => isModelExhausted(model));
        if (exhaustedSelection) {
          setLoading(false);

          // Check if ANY model combination can work (even with 1 turn)
          const allModelsExhausted = modelKeys.every(model => isModelExhausted(model));

          if (allModelsExhausted) {
            // No models available at all
            setError({
              userMessage: 'All free uses have been exhausted for today.',
              suggestion: 'Please add your own API keys below or return tomorrow.',
              category: 'RATE_LIMITED',
              isRetryable: false
            });
          } else {
            // Specific selected models are exhausted, but others might work
            setError({
              userMessage: 'The selected models do not have sufficient free uses remaining for this debate.',
              suggestion: 'Please try different models, reduce the number of turns, or add your own API keys below.',
              category: 'RATE_LIMITED',
              isRetryable: false
            });
          }
          return;
        }
      }

      let completedSteps = 0;
      let totalSteps = turns * 2 + 1;
      let streamError: string | null = null;
      let historyLength = 0;
      let lastActionSummary = '';

      const getProgressPercentage = (completed: number, total: number) => {
        if (total <= 0) {
          return 100;
        }
        const raw = (completed / total) * 100;
        const rounded = Math.round(raw / 5) * 5;
        return Math.min(100, Math.max(5, rounded));
      };

      const applyProgress = (completed: number, total: number) => {
        setProgress(getProgressPercentage(completed, total));
      };

      const response = await fetch('/api/debate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Debate-Stream': '1'
        },
        body: JSON.stringify({
          claim,
          turns,
          proModel,
          conModel,
          judgeModel,
          firstSpeaker,
          userApiKeys
        })
      });

      if (!response.ok) {
        try {
          const errorPayload = await response.json();
          // Check if it's our new structured error format
          if (errorPayload.userMessage) {
            throw new Error(JSON.stringify(errorPayload));
          }
          // Fallback to old format
          const message = errorPayload.message || errorPayload.error || 'Failed to run debate';
          throw new Error(message);
        } catch (jsonError) {
          const text = await response.text();
          throw new Error(text || 'Failed to run debate');
        }
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Unable to read debate progress stream.');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      const getEffectiveTotalTurns = () =>
        Math.max(1, Math.floor(Math.max(totalSteps - 1, 1) / 2));

      const getSideLabelForIndex = (index: number) => {
        const sequence = firstSpeaker === 'pro' ? ['Pro', 'Con'] : ['Con', 'Pro'];
        return sequence[index % 2];
      };

      const buildNextActionText = (remainingSteps: number, currentHistoryLength: number) => {
        if (remainingSteps <= 0) {
          return '';
        }
        if (remainingSteps === 1) {
          return `Judge (${judgeModelName}) now deliberating...`;
        }
        const nextIndex = currentHistoryLength;
        const nextTurnNum = Math.floor(nextIndex / 2) + 1;
        const effectiveTotalTurns = getEffectiveTotalTurns();
        const nextSideLabel = getSideLabelForIndex(nextIndex);
        const nextModelName = nextSideLabel === 'Pro' ? proModelName : conModelName;
        return `${nextSideLabel} side (${nextModelName}) now making an argument in turn ${nextTurnNum}/${effectiveTotalTurns}...`;
      };

      const handleEvent = (rawEvent: any) => {
        if (!rawEvent || typeof rawEvent.type !== 'string') {
          return;
        }

        switch (rawEvent.type) {
          case 'init': {
            if (typeof rawEvent.totalSteps === 'number') {
              totalSteps = rawEvent.totalSteps;
            }
            completedSteps = 0;
            applyProgress(completedSteps, totalSteps);
            break;
          }
          case 'total_steps': {
            if (typeof rawEvent.totalSteps === 'number') {
              totalSteps = rawEvent.totalSteps;
            }
            if (typeof rawEvent.completedSteps === 'number') {
              completedSteps = rawEvent.completedSteps;
            }
            applyProgress(completedSteps, totalSteps);
            break;
          }
          case 'turn': {
            if (typeof rawEvent.totalSteps === 'number') {
              totalSteps = rawEvent.totalSteps;
            }
            if (typeof rawEvent.completedSteps === 'number') {
              completedSteps = rawEvent.completedSteps;
            } else {
              completedSteps += 1;
            }

            if (rawEvent.turn) {
              const turnIndex = historyLength;
              historyLength += 1;
              setDebateHistory(prev => [...prev, rawEvent.turn]);
              const effectiveTotalTurns = getEffectiveTotalTurns();
              const turnNum = Math.floor(turnIndex / 2) + 1;
              const position = rawEvent.turn.position;
              const modelName = rawEvent.turn.model;
              const refused = rawEvent.turn.refused;
              const sideLabel = position === 'pro' ? 'Pro' : 'Con';
              const completedText = refused
                ? `${sideLabel} side (${modelName}) declined to argue in turn ${turnNum}/${effectiveTotalTurns}.`
                : `${sideLabel} side (${modelName}) finished their argument in turn ${turnNum}/${effectiveTotalTurns}.`;
              lastActionSummary = completedText;
              const remainingSteps = Math.max(totalSteps - completedSteps, 0);
              const nextText = buildNextActionText(remainingSteps, historyLength);
              setProgressMessage({
                primary: completedText,
                secondary: nextText || undefined
              });
            }

            applyProgress(completedSteps, totalSteps);
            break;
          }
          case 'judge_pending': {
            if (typeof rawEvent.totalSteps === 'number') {
              totalSteps = rawEvent.totalSteps;
            }
            if (typeof rawEvent.completedSteps === 'number') {
              completedSteps = rawEvent.completedSteps;
            }
            applyProgress(completedSteps, totalSteps);
            const judgeName = rawEvent.model || judgeModelName;
            const judgeMsg = `Judge (${judgeName}) now deliberating...`;
            if (lastActionSummary) {
              setProgressMessage({
                primary: lastActionSummary,
                secondary: judgeMsg
              });
            } else {
              setProgressMessage({
                primary: judgeMsg
              });
            }
            break;
          }
          case 'verdict': {
            if (typeof rawEvent.totalSteps === 'number') {
              totalSteps = rawEvent.totalSteps;
            }
            if (typeof rawEvent.completedSteps === 'number') {
              completedSteps = rawEvent.completedSteps;
            } else {
              completedSteps += 1;
            }
            if (rawEvent.verdict) {
              setVerdict(rawEvent.verdict);
            }
            applyProgress(completedSteps, totalSteps);
            setProgressMessage({
              primary: `Judge (${judgeModelName}) delivered the verdict.`,
              secondary: undefined
            });
            break;
          }
          case 'complete': {
            if (rawEvent.result?.debate_history && rawEvent.result.debate_history.length > 0) {
              setDebateHistory(rawEvent.result.debate_history);
              historyLength = rawEvent.result.debate_history.length;
            }
            if (rawEvent.result?.verdict && !verdict) {
              setVerdict(rawEvent.result.verdict);
            }
            break;
          }
          case 'error': {
            // Handle new structured error format
            if (rawEvent.userMessage) {
              streamError = JSON.stringify({
                userMessage: rawEvent.userMessage,
                suggestion: rawEvent.suggestion,
                provider: rawEvent.provider,
                model: rawEvent.model,
                category: rawEvent.category,
                isRetryable: rawEvent.isRetryable,
                completedSteps: rawEvent.completedSteps
              });
            } else {
              // Fallback for old format
              streamError = rawEvent.message || 'Failed to run debate';
            }
            break;
          }
          default:
            break;
        }
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let newlineIndex = buffer.indexOf('\n');
        while (newlineIndex !== -1) {
          const line = buffer.slice(0, newlineIndex).trim();
          buffer = buffer.slice(newlineIndex + 1);
          if (line.length > 0) {
            try {
              const parsed = JSON.parse(line);
              handleEvent(parsed);
            } catch (parseErr) {
              console.warn('Failed to parse debate stream chunk:', parseErr, line);
            }
          }
          newlineIndex = buffer.indexOf('\n');
        }
      }

      const remaining = buffer.trim();
      if (remaining) {
        try {
          const parsed = JSON.parse(remaining);
          handleEvent(parsed);
        } catch (parseErr) {
          console.warn('Failed to parse final debate stream chunk:', parseErr, remaining);
        }
      }

      if (streamError) {
        throw new Error(streamError);
      }

      // Refresh rate limits so UI reflects the latest usage
      if (usingServerKeys) {
        await fetchRateLimits();
      }
    } catch (err: any) {
      // Try to parse structured error
      try {
        const errorData = JSON.parse(err.message);
        if (errorData.userMessage) {
          setError(errorData);
        } else {
          setError({ userMessage: err.message });
        }
      } catch {
        // Not JSON, just use the message
        setError({ userMessage: err.message });
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Head>
        <title>AI Debates</title>
        <meta name="description" content={description} />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/icons/ai-debate.ico" sizes="any" />
        <link rel="icon" type="image/png" href="/icons/ai-debate-32x32.png" sizes="32x32" />
        <link rel="icon" type="image/png" href="/icons/ai-debate-16x16.png" sizes="16x16" />
        <link rel="apple-touch-icon" href="/icons/apple-touch-icon.png" sizes="180x180" />
        <link rel="manifest" href="/site.webmanifest" />
        <meta name="theme-color" content="#ffffff" />
        <meta property="og:type" content="website" />
        <meta property="og:title" content="AI Debates" />
        <meta property="og:description" content={description} />
        {siteUrl && <meta property="og:url" content={siteUrl} />}
        <meta property="og:image" content={ogImageUrl} />
        <meta property="og:image:width" content="1200" />
        <meta property="og:image:height" content="630" />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content="AI Debates" />
        <meta name="twitter:description" content={description} />
        <meta name="twitter:image" content={twitterImageUrl} />
      </Head>

      <div className="page">
        <section className="hero-section">
          <div className="hero-card hero-text">
            <h1 className="hero-title">AI Debates</h1>
            <p className="hero-subtitle">
              Adversarial Truth-Seeking Through Structured Debates
            </p>
            <p className="hero-description">
              A{' '}
              <a
                href="https://github.com/aaron1729/ai-debate/blob/main/README.md"
                target="_blank"
                rel="noopener noreferrer"
              >
                Modernization
              </a>{' '}
              Of{' '}
              <a href="https://arxiv.org/abs/1805.00899" target="_blank" rel="noopener noreferrer">
                AI Safety Via Debate
              </a>{' '}
              (Irving et al., 2018)
            </p>
            <p className="hero-description fine-print">
              Judge Evaluation Based On{' '}
              <a href="http://www.paulgraham.com/disagree.html" target="_blank" rel="noopener noreferrer">
                Paul Graham&apos;s Disagreement Hierarchy
              </a>
            </p>
          </div>

          <div className="hero-card hero-image">
            <picture>
              <source srcSet="/hero/ai-debate-display-2400x1260.webp" type="image/webp" />
              <img
                src="/hero/ai-debate-display-2400x1260.png"
                alt="Illustration representing AI debate participants"
                loading="lazy"
                decoding="async"
              />
            </picture>
          </div>
        </section>

        {/* Sample Debates Section */}
        {sampleDebates.length > 0 && (
          <section className="sample-debates-section">
            <h2 className="sample-debates-heading">Choose a sample debate to run:</h2>
            <div className="sample-debates-grid" ref={(el) => {
              if (el) {
                console.log('[Render] Sample debates cards rendered in DOM', {
                  timestamp: Date.now(),
                  cardCount: sampleDebates.length
                });
              }
            }}>
              {sampleDebates.map((sample) => (
                <div
                  key={sample.id}
                  className={`sample-card ${loading ? 'loading' : ''}`}
                  onClick={() => handleSampleClick(sample)}
                  role="button"
                  tabIndex={loading ? -1 : 0}
                  onKeyDown={(e) => {
                    if ((e.key === 'Enter' || e.key === ' ') && !loading) {
                      e.preventDefault();
                      handleSampleClick(sample);
                    }
                  }}
                  aria-disabled={loading}
                >
                  <div className="sample-claim">{sample.claim}</div>
                  <div className="sample-metadata">
                    <div className="sample-debaters">
                      Pro: {MODELS[sample.proModel].name} • Con: {MODELS[sample.conModel].name}
                    </div>
                    <div className="sample-judge">Judge: {MODELS[sample.judgeModel].name}</div>
                    <div className="sample-turns">
                      {sample.turns} {sample.turns === 1 ? 'turn' : 'turns'} • {sample.openingSide === 'pro' ? 'Pro' : 'Con'} argues first
                    </div>
                  </div>
                  <button type="button" className="sample-button" disabled={loading}>
                    Run this debate!
                  </button>
                </div>
              ))}
            </div>
          </section>
        )}

        {sampleDebates.length > 0 && (
          <h2 className="create-your-own-heading">Or, create your own!</h2>
        )}

        <form onSubmit={handleSubmit} style={{ marginBottom: '40px' }}>
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
              Claim to Debate:
            </label>
            <textarea
              value={claim}
              onChange={(e) => setClaim(e.target.value)}
              placeholder="Enter a factual claim to debate..."
              required
              disabled={loading}
              style={{
                width: '100%',
                minHeight: '80px',
                padding: '10px',
                fontSize: '14px',
                border: '1px solid #e7d7c7',
                borderRadius: '6px',
                background: '#fefaf5',
                boxSizing: 'border-box',
                outline: 'none',
                transition: 'box-shadow 0.2s ease, border-color 0.2s ease'
              }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '15px' }}>
            <div>
              <label htmlFor="pro-model" style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                Pro Model:
              </label>
              <select
                id="pro-model"
                value={proModel}
                onChange={(e) => setProModel(e.target.value as ModelKey)}
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '8px',
                  fontSize: '13px',
                  border: '1px solid #e7d7c7',
                  borderRadius: '6px',
                  background: '#fefaf5',
                  boxSizing: 'border-box',
                  outline: 'none',
                  transition: 'box-shadow 0.2s ease, border-color 0.2s ease'
                }}
              >
                {modelKeys.map(key => {
                  const disabledOption = usingServerKeys && isModelExhausted(key);
                  return (
                    <option
                      key={key}
                      value={key}
                      disabled={disabledOption}
                      style={{
                        color: disabledOption ? '#ccc' : 'inherit'
                      }}
                    >
                      {MODELS[key].name}
                    </option>
                  );
                })}
              </select>
            </div>

            <div>
              <label htmlFor="con-model" style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                Con Model:
              </label>
              <select
                id="con-model"
                value={conModel}
                onChange={(e) => setConModel(e.target.value as ModelKey)}
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '8px',
                  fontSize: '13px',
                  border: '1px solid #e7d7c7',
                  borderRadius: '6px',
                  background: '#fefaf5',
                  boxSizing: 'border-box',
                  outline: 'none',
                  transition: 'box-shadow 0.2s ease, border-color 0.2s ease'
                }}
              >
                {modelKeys.map(key => {
                  const disabledOption = usingServerKeys && isModelExhausted(key);
                  return (
                    <option
                      key={key}
                      value={key}
                      disabled={disabledOption}
                      style={{
                        color: disabledOption ? '#ccc' : 'inherit'
                      }}
                    >
                      {MODELS[key].name}
                    </option>
                  );
                })}
              </select>
            </div>

            <div>
              <label htmlFor="judge-model" style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                Judge Model:
              </label>
              <select
                id="judge-model"
                value={judgeModel}
                onChange={(e) => setJudgeModel(e.target.value as ModelKey)}
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '8px',
                  fontSize: '13px',
                  border: '1px solid #e7d7c7',
                  borderRadius: '6px',
                  background: '#fefaf5',
                  boxSizing: 'border-box',
                  outline: 'none',
                  transition: 'box-shadow 0.2s ease, border-color 0.2s ease'
                }}
              >
                {modelKeys.map(key => {
                  const disabledOption = usingServerKeys && isModelExhausted(key);
                  return (
                    <option
                      key={key}
                      value={key}
                      disabled={disabledOption}
                      style={{
                        color: disabledOption ? '#ccc' : 'inherit'
                      }}
                    >
                      {MODELS[key].name}
                    </option>
                  );
                })}
              </select>
            </div>

            <div>
              <label htmlFor="turns" style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                Number of Turns:
              </label>
              <select
                id="turns"
                value={turns}
                onChange={(e) => setTurns(parseInt(e.target.value))}
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '8px',
                  fontSize: '13px',
                  border: '1px solid #e7d7c7',
                  borderRadius: '6px',
                  background: '#fefaf5',
                  boxSizing: 'border-box',
                  outline: 'none',
                  transition: 'box-shadow 0.2s ease, border-color 0.2s ease'
                }}
              >
                {[1, 2, 3, 4, 5, 6].map(n => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>
          </div>

          <div style={{
            padding: '10px 12px 12px',
            background: '#fdf9f4',
            border: '1px solid #eddccf',
            borderRadius: '4px',
            marginBottom: '20px'
          }}>
            <p style={{ fontSize: '13px', fontWeight: 'bold', margin: '0 0 8px', color: '#374151' }}>
              Free uses remaining today:
            </p>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '8px' }}>
              {modelKeys.map(key => {
                const info = modelLimits[key];
                const remaining = Math.max(0, info?.remaining ?? rateLimit);
                const color = remaining <= 0 ? '#ef4444' : '#6b7280';
                return (
                  <div key={key} style={{ fontSize: '12px', color }}>
                    <strong>{MODELS[key].name}:</strong> {remaining}/{rateLimit}
                    {info?.globalRemaining !== undefined && info.globalRemaining <= 0 && (
                      <span style={{ display: 'block', color: '#b91c1c', marginTop: '4px' }}>
                        Global limit reached — add your own API key or come back tomorrow.
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {usingServerKeys && hasLoadedLimits && allServerModelsExhausted && (
            <div style={{
              padding: '12px',
              background: '#fff7ed',
              border: '1px solid #fb923c',
              borderRadius: '4px',
              marginBottom: '20px',
              color: '#9a3412',
              fontSize: '13px'
            }}>
              Your free-tier usage has been exhausted. Add your own API keys below, or wait for the 24-hour window to reset.
            </div>
          )}

          <div style={{ marginBottom: '20px' }}>
            <button
              type="button"
              onClick={() => setShowApiKeys(!showApiKeys)}
              disabled={loading}
              style={{
                background: 'none',
                border: 'none',
                color: '#18636d',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: '14px',
                textDecoration: 'underline',
                padding: 0
              }}
            >
              {showApiKeys ? 'Hide' : 'Use API Keys'}
            </button>
            <span style={{ marginLeft: '6px', fontSize: '13px', color: '#4b5563' }}>(optional, for unlimited usage)</span>

            {showApiKeys && (
              <div style={{
                marginTop: '8px',
                padding: '10px 15px 15px',
                background: '#fefbf6',
                borderRadius: '4px'
              }}>
                <p style={{ fontSize: '13px', color: '#666', margin: '0 0 8px', lineHeight: 1.5 }}>
                  You get {rateLimit} free uses per model per day. Add your own API keys here for unlimited usage.
                  <span style={{ display: 'block', marginTop: '4px' }}>(These are only stored in your browser, and disappear when you leave or refresh the page.)</span>
                </p>
                <div style={{ display: 'grid', gap: '10px' }}>
                  <input
                    type="password"
                    placeholder="Anthropic API Key (optional)"
                    value={apiKeys.anthropic}
                    onChange={(e) => setApiKeys({ ...apiKeys, anthropic: e.target.value })}
                    disabled={loading}
                    style={{
                      padding: '8px',
                      fontSize: '13px',
                      border: '1px solid #e7d7c7',
                      borderRadius: '6px',
                      background: '#fefaf5',
                      boxSizing: 'border-box',
                      outline: 'none',
                      transition: 'box-shadow 0.2s ease, border-color 0.2s ease'
                    }}
                  />
                  <input
                    type="password"
                    placeholder="OpenAI API Key (optional)"
                    value={apiKeys.openai}
                    onChange={(e) => setApiKeys({ ...apiKeys, openai: e.target.value })}
                    disabled={loading}
                    style={{
                      padding: '8px',
                      fontSize: '13px',
                      border: '1px solid #e7d7c7',
                      borderRadius: '6px',
                      background: '#fefaf5',
                      boxSizing: 'border-box',
                      outline: 'none',
                      transition: 'box-shadow 0.2s ease, border-color 0.2s ease'
                    }}
                  />
                  <input
                    type="password"
                    placeholder="Google API Key (optional)"
                    value={apiKeys.google}
                    onChange={(e) => setApiKeys({ ...apiKeys, google: e.target.value })}
                    disabled={loading}
                    style={{
                      padding: '8px',
                      fontSize: '13px',
                      border: '1px solid #e7d7c7',
                      borderRadius: '6px',
                      background: '#fefaf5',
                      boxSizing: 'border-box',
                      outline: 'none',
                      transition: 'box-shadow 0.2s ease, border-color 0.2s ease'
                    }}
                  />
                  <input
                    type="password"
                    placeholder="xAI API Key (optional)"
                    value={apiKeys.xai}
                    onChange={(e) => setApiKeys({ ...apiKeys, xai: e.target.value })}
                    disabled={loading}
                    style={{
                      padding: '8px',
                      fontSize: '13px',
                      border: '1px solid #e7d7c7',
                      borderRadius: '6px',
                      background: '#fefaf5',
                      boxSizing: 'border-box',
                      outline: 'none',
                      transition: 'box-shadow 0.2s ease, border-color 0.2s ease'
                    }}
                  />
                </div>
              </div>
            )}
          </div>

          <div className="form-actions">
            <div className="starting-side-toggle">
              <span className="toggle-label">Opening Side:</span>
              <div
                className="toggle-control"
                role="group"
                aria-label="Select opening side"
              >
                <span
                  className="toggle-highlight"
                  style={{ transform: firstSpeaker === 'pro' ? 'translateX(0)' : 'translateX(100%)' }}
                  aria-hidden="true"
                />
                <button
                  type="button"
                  className={`toggle-button${firstSpeaker === 'pro' ? ' active' : ''}`}
                  aria-pressed={firstSpeaker === 'pro'}
                  onClick={() => setFirstSpeaker('pro')}
                  disabled={loading}
                >
                  Pro
                </button>
                <button
                  type="button"
                  className={`toggle-button${firstSpeaker === 'con' ? ' active' : ''}`}
                  aria-pressed={firstSpeaker === 'con'}
                  onClick={() => setFirstSpeaker('con')}
                  disabled={loading}
                >
                  Con
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="start-button"
              disabled={loading || (usingServerKeys && allServerModelsExhausted)}
            >
              {loading ? 'Running Debate...' : 'Start Debate!'}
            </button>
          </div>
        </form>

        {loading && (
          <div style={{ marginBottom: '20px', textAlign: 'center' }}>
            <div style={{
              width: '100%',
              height: '30px',
              background: '#f1e4d8',
              borderRadius: '4px',
              overflow: 'hidden',
              position: 'relative'
            }}>
              <div style={{
                width: `${Math.max(progress, 10)}%`,
                height: '100%',
                background: '#0070f3',
                transition: 'width 0.3s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontSize: '14px',
                fontWeight: 'bold',
                minWidth: '40px'
              }}>
                {Math.round(progress)}%
              </div>
            </div>
            <div style={{ marginTop: '8px', color: '#666', fontSize: '14px' }}>
              {progressMessage.primary && (
                <p style={{ margin: 0 }}>{progressMessage.primary}</p>
              )}
              {progressMessage.secondary && (
                <p style={{ margin: '4px 0 0 0' }}>{progressMessage.secondary}</p>
              )}
            </div>
          </div>
        )}

        {error && (
          <div style={{
            padding: '20px',
            background: '#fee',
            border: '2px solid #fcc',
            borderRadius: '8px',
            marginBottom: '20px',
            color: '#333'
          }}>
            <div style={{ marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '24px' }}>⚠️</span>
              <strong style={{ fontSize: '18px', color: '#c00' }}>Error</strong>
              {error.model && (
                <span style={{
                  fontSize: '12px',
                  padding: '2px 8px',
                  background: '#fdd',
                  borderRadius: '4px',
                  color: '#800'
                }}>
                  {error.model}
                </span>
              )}
            </div>

            <p style={{ margin: '10px 0', fontSize: '16px', lineHeight: '1.5' }}>
              {error.userMessage}
            </p>

            {error.suggestion && (
              <p style={{
                margin: '10px 0',
                padding: '10px',
                background: '#fff',
                border: '1px solid #fbb',
                borderRadius: '4px',
                fontSize: '14px',
                lineHeight: '1.5'
              }}>
                <strong>Suggestion:</strong> {error.suggestion}
              </p>
            )}

            {error.completedSteps !== undefined && error.completedSteps > 0 && (
              <p style={{ margin: '10px 0 0 0', fontSize: '14px', color: '#666' }}>
                The debate completed {error.completedSteps} step{error.completedSteps !== 1 ? 's' : ''} before this error occurred.
              </p>
            )}

            {error.isRetryable && (
              <button
                onClick={(e) => {
                  setError(null);
                  handleSubmit(e as any);
                }}
                disabled={loading}
                style={{
                  marginTop: '15px',
                  padding: '10px 20px',
                  background: loading ? '#6c757d' : '#007bff',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  fontSize: '14px',
                  fontWeight: 'bold',
                  opacity: loading ? 0.6 : 1
                }}
                onMouseOver={(e) => !loading && (e.currentTarget.style.background = '#0056b3')}
                onMouseOut={(e) => !loading && (e.currentTarget.style.background = '#007bff')}
              >
                {loading ? 'Retrying...' : 'Try Again'}
              </button>
            )}
          </div>
        )}

        {verdict && (
          <div style={{
            padding: '20px',
            background: '#f0f8ff',
            border: '2px solid #add8e6',
            borderRadius: '4px',
            marginBottom: '30px',
            animation: 'fadeIn 0.5s ease-in'
          }}>
            <h2 style={{ marginTop: 0, marginBottom: '15px' }}>Final Verdict</h2>
            <p style={{ fontSize: '18px', marginBottom: '10px' }}>
              <strong>Verdict: </strong>
              <span style={{
                color: getVerdictColor(verdict.verdict),
                fontWeight: 'bold',
                fontSize: '20px'
              }}>
                {verdict.verdict.toUpperCase()}
              </span>
            </p>
            <p style={{ fontSize: '16px', lineHeight: '1.6' }}>
              <strong>Explanation:</strong> {verdict.explanation}
            </p>
          </div>
        )}

        {debateHistory.length > 0 && (
          <div>
            <h2 style={{ marginBottom: '20px' }}>Debate Transcript</h2>
            {debateHistory.map((turn, i) => (
              <div
                key={i}
                style={{
                  padding: '15px',
                  marginBottom: '15px',
                  background: turn.position === 'pro' ? '#e8f5e9' : '#ffebee',
                  border: turn.position === 'pro' ? '1px solid #a5d6a7' : '1px solid #ef9a9a',
                  borderRadius: '4px',
                  animation: 'fadeIn 0.3s ease-in'
                }}
              >
                <h4 style={{ margin: '0 0 10px 0' }}>
                  Turn {Math.floor(i / 2) + 1} - {turn.position.toUpperCase()} ({turn.model})
                </h4>

                {turn.refused ? (
                  <div>
                    <p style={{ fontStyle: 'italic', color: '#666' }}>[REFUSED TO ARGUE]</p>
                    <p><strong>Reason:</strong> {turn.refusal_reason}</p>
                  </div>
                ) : (
                  <div>
                    <p><strong>Source:</strong> <a href={turn.url} target="_blank" rel="noopener noreferrer" style={{ color: '#18636d' }}>{turn.url}</a></p>
                    <p><strong>Quote:</strong> &quot;{turn.quote}&quot;</p>
                    <p><strong>Context:</strong> {turn.context}</p>
                    <p><strong>Argument:</strong> {turn.argument}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        <style jsx>{`
          .page {
            max-width: 1280px;
            margin: 0 auto;
            padding: 20px 24px 60px;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          }

          .hero-section {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 28px;
            margin-bottom: 48px;
          }

          .hero-card {
            flex: 1 1 0;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: clamp(12px, 4vw, 20px);
            width: 100%;
            box-sizing: border-box;
          }

          .hero-text {
            max-width: 540px;
            margin: 0 auto;
            gap: 12px;
            order: 2;
          }

          .hero-title {
            margin: 0 0 10px;
            font-size: clamp(2.25rem, 3vw, 2.8rem);
            line-height: 1.1;
          }

          .hero-subtitle {
            margin: 0 0 12px;
            color: #555;
            font-size: clamp(1.05rem, 2.2vw, 1.2rem);
          }

          .hero-description {
            margin: 0 0 6px;
            font-size: 0.9rem;
            color: #777;
          }

          .hero-description.fine-print {
            font-size: 0.85rem;
            color: #888;
            margin-bottom: 0;
          }

          .hero-description a {
            color: #18636d;
            text-decoration: none;
          }

          .hero-description a:hover,
          .hero-description a:focus {
            text-decoration: underline;
          }

          .hero-image {
            width: 100%;
            max-width: 420px;
            margin: 0 auto;
            order: 1;
            display: flex;
            justify-content: center;
            align-items: center;
          }

          .hero-image picture {
            display: block;
            width: clamp(240px, 75vw, 420px);
            margin: 0 auto;
          }

          .hero-image img {
            width: 100%;
            height: auto;
            max-height: clamp(200px, 55vw, 300px);
            display: block;
            border-radius: 16px;
            box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
            aspect-ratio: 2400 / 1260;
            margin: 0 auto;
          }

          .form-actions {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 24px;
            margin-top: 32px;
            width: 100%;
            max-width: 540px;
            margin-left: auto;
            margin-right: auto;
            padding: 0 16px;
          }

          .starting-side-toggle {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            flex-wrap: wrap;
            width: auto;
            text-align: center;
          }

          .starting-side-toggle .toggle-label {
            font-size: 0.9rem;
            font-weight: 500;
            color: #1f2937;
            white-space: nowrap;
          }

          .starting-side-toggle .toggle-control {
            position: relative;
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            border: 1px solid #eddccf;
            border-radius: 9999px;
            padding: 3px;
            background: #fdf9f4;
            min-width: 210px;
            overflow: hidden;
          }

          .toggle-highlight {
            position: absolute;
            top: 3px;
            left: 3px;
            width: calc(50% - 3px);
            height: calc(100% - 6px);
            background: #c46b36;
            border-radius: 9999px;
            box-shadow: 0 10px 22px rgba(196, 107, 54, 0.35);
            transition: transform 0.25s ease;
            pointer-events: none;
            z-index: 0;
          }

          .toggle-button {
            position: relative;
            z-index: 1;
            border: none;
            background: transparent;
            padding: 5px 12px;
            font-size: 0.82rem;
            font-weight: 500;
            color: #4b5563;
            border-radius: 9999px;
            cursor: pointer;
            transition: color 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
          }

          .toggle-button.active {
            color: #fff7f2;
          }

          .toggle-button:focus-visible {
            outline: 2px solid rgba(196, 107, 54, 0.65);
            outline-offset: 2px;
            border-radius: 9999px;
          }

          .toggle-button:disabled {
            cursor: not-allowed;
            opacity: 0.55;
          }

          .start-button {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 12px 36px;
            font-size: 16px;
            font-weight: 600;
            color: #fff8f4;
            background: ${loading || (usingServerKeys && allServerModelsExhausted) ? '#d1d5db' : '#c46b36'};
            border: none;
            border-radius: 9999px;
            box-shadow: ${loading || (usingServerKeys && allServerModelsExhausted) ? 'none' : '0 14px 28px rgba(196, 107, 54, 0.28)'};
            cursor: ${loading || (usingServerKeys && allServerModelsExhausted) ? 'not-allowed' : 'pointer'};
            transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
            min-width: 180px;
            text-align: center;
            opacity: ${loading || (usingServerKeys && allServerModelsExhausted) ? 0.85 : 1};
          }

          .start-button:hover:not(:disabled),
          .start-button:focus-visible:not(:disabled) {
            transform: translateY(-1px);
            box-shadow: 0 18px 34px rgba(196, 107, 54, 0.34);
            background: #ba5f2b;
          }

          .start-button:focus-visible {
            outline: 2px solid rgba(196, 107, 54, 0.55);
            outline-offset: 3px;
          }

          textarea:focus,
          select:focus,
          input:focus {
            border-color: #18636d;
            box-shadow: 0 0 0 3px #18636d40;
          }

          textarea:hover,
          select:hover,
          input:hover {
            border-color: rgba(24, 99, 109, 0.7);
            background-color: #fef2eb;
          }

          @media (min-width: 960px) {
            .hero-text {
              order: 1;
              min-height: clamp(260px, 28vw, 320px);
            }

            .hero-image {
              order: 2;
            }

            .hero-image img {
              width: 100%;
              max-width: 100%;
              margin: 0 auto;
            }

            .hero-section {
              flex-direction: row;
              justify-content: center;
              gap: 48px;
              padding: 0 12px;
            }

            .hero-card {
              align-items: center;
            }

            .hero-text,
            .hero-image {
              margin: 0;
            }

            .form-actions {
              flex-direction: row;
              align-items: center;
              justify-content: center;
              gap: clamp(72px, 14vw, 128px);
              padding: 0 24px;
              margin-left: auto;
              margin-right: auto;
            }

            .starting-side-toggle {
              justify-content: center;
              flex-wrap: nowrap;
            }
          }

          @media (min-width: 1280px) {
            .page {
              max-width: 1400px;
            }

            .hero-section {
              gap: 56px;
              padding: 0 32px;
            }
          }

          /* Sample Debates Section */
          .sample-debates-section {
            margin-bottom: 48px;
          }

          .sample-debates-heading {
            font-size: 18px;
            font-weight: bold;
            color: #374151;
            margin: 0 0 20px 0;
            text-align: center;
          }

          .create-your-own-heading {
            font-size: 18px;
            font-weight: bold;
            color: #374151;
            margin: 0 0 20px 0;
            text-align: center;
          }

          .sample-debates-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 32px;
          }

          .sample-card {
            position: relative;
            display: flex;
            flex-direction: column;
            gap: 12px;
            padding: 16px;
            background: #fefaf5;
            border: 1px solid #e7d7c7;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s ease;
          }

          .sample-card:not(.disabled):not(.loading):hover {
            border-color: #c46b36;
            box-shadow: 0 2px 8px rgba(196, 107, 54, 0.15);
            transform: translateY(-1px);
          }

          .sample-card:not(.disabled):not(.loading):focus {
            outline: 2px solid #c46b36;
            outline-offset: 2px;
          }

          .sample-card.loading {
            opacity: 0.5;
            pointer-events: none;
          }

          .sample-claim {
            font-size: 14px;
            font-weight: bold;
            color: #1f2937;
            line-height: 1.4;
          }

          .sample-metadata {
            display: flex;
            flex-direction: column;
            gap: 4px;
            font-size: 12px;
            color: #6b7280;
          }

          .sample-debaters {
            font-size: 12px;
          }

          .sample-judge {
            font-size: 12px;
          }

          .sample-turns {
            font-size: 11px;
            color: #9ca3af;
          }

          .sample-button {
            margin-top: auto;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 600;
            color: white;
            background: #c46b36;
            border: none;
            border-radius: 9999px;
            cursor: pointer;
            transition: background 0.2s ease;
          }

          .sample-button:not(:disabled):hover {
            background: #a85a2e;
          }

          .sample-button:disabled {
            cursor: not-allowed;
            opacity: 0.7;
          }

          /* Tablet: 2 columns, all 6 cards */
          @media (max-width: 900px) {
            .sample-debates-grid {
              grid-template-columns: repeat(2, 1fr);
            }
          }

          /* Mobile: 1 column, show only 2 cards */
          @media (max-width: 600px) {
            .sample-debates-grid {
              grid-template-columns: 1fr;
            }

            .sample-card:nth-child(n+3) {
              display: none;
            }
          }

          @keyframes fadeIn {
            from {
              opacity: 0;
              transform: translateY(10px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }
        `}</style>
        <style jsx global>{`
          body {
            background: #f8efe4;
          }
        `}</style>
      </div>
    </>
  );
}
