import { useState, useEffect, useCallback } from 'react';
import Head from 'next/head';
import { MODELS, ModelKey, DebateResult, DebateTurn } from '../lib/debate-engine';
import messages from '../shared/messages.json';

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
  const [proModel, setProModel] = useState<ModelKey>('claude');
  const [conModel, setConModel] = useState<ModelKey>('claude');
  const [judgeModel, setJudgeModel] = useState<ModelKey>('claude');
  const [loading, setLoading] = useState(false);
  type ProgressMessage = { primary: string; secondary?: string };
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState<ProgressMessage>({ primary: '', secondary: undefined });
  const [debateHistory, setDebateHistory] = useState<DebateTurn[]>([]);
  const [verdict, setVerdict] = useState<DebateResult['verdict'] | null>(null);
  const [error, setError] = useState<string | null>(null);
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

  const description = 'Adversarial truth-seeking through structured AI debates';
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
    try {
      const response = await fetch('/api/check-rate-limit', { cache: 'no-store' });
      if (!response.ok) {
        return;
      }

      const data = await response.json();
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
    } catch (err) {
      console.error('Failed to check rate limit:', err);
    }
  }, []);

  // Fetch initial rate limit and usage on page load
  useEffect(() => {
    fetchRateLimits();
  }, [fetchRateLimits]);

  const getVerdictColor = (verdictType: string) => {
    switch (verdictType) {
      case 'supported': return '#22c55e'; // green
      case 'contradicted': return '#ef4444'; // red
      case 'misleading': return '#f59e0b'; // orange
      case 'needs more evidence': return '#6b7280'; // gray
      default: return '#3b82f6'; // blue
    }
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
    setProgressMessage({
      primary: cleanedStart,
      secondary: `Pro side (${proModelName}) now making an argument in turn 1/${Math.max(turns, 1)}...`
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
          setError('The selected model(s) have no free-tier runs remaining. Provide your own API keys or wait for the 24-hour window to reset.');
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
          userApiKeys
        })
      });

      if (!response.ok) {
        let message = 'Failed to run debate';
        try {
          const errorPayload = await response.json();
          message = errorPayload.message || errorPayload.error || message;
        } catch {
          const text = await response.text();
          if (text) {
            message = text;
          }
        }
        throw new Error(message);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('Unable to read debate progress stream.');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      const getEffectiveTotalTurns = () =>
        Math.max(1, Math.floor(Math.max(totalSteps - 1, 1) / 2));

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
        const nextSideLabel = nextIndex % 2 === 0 ? 'Pro' : 'Con';
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
            streamError = rawEvent.message || 'Failed to run debate';
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
      setError(err.message);
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
              Adversarial truth-seeking through structured debates
            </p>
            <p className="hero-description">
              A modernization of{' '}
              <a href="https://arxiv.org/abs/1805.00899" target="_blank" rel="noopener noreferrer">
                AI safety via debate
              </a>{' '}
              (Irving et al., 2018)
            </p>
            <p className="hero-description fine-print">
              Judge evaluation based on{' '}
              <a href="http://www.paulgraham.com/disagree.html" target="_blank" rel="noopener noreferrer">
                Paul Graham&apos;s disagreement hierarchy
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

        <form onSubmit={handleSubmit} style={{ marginBottom: '40px' }}>
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
              Claim to debate:
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
                border: '1px solid #ddd',
                borderRadius: '4px'
              }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '15px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                Pro Model:
              </label>
              <select
                value={proModel}
                onChange={(e) => setProModel(e.target.value as ModelKey)}
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '8px',
                  fontSize: '14px',
                  border: '1px solid #ddd',
                  borderRadius: '4px'
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
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                Con Model:
              </label>
              <select
                value={conModel}
                onChange={(e) => setConModel(e.target.value as ModelKey)}
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '8px',
                  fontSize: '14px',
                  border: '1px solid #ddd',
                  borderRadius: '4px'
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
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                Judge Model:
              </label>
              <select
                value={judgeModel}
                onChange={(e) => setJudgeModel(e.target.value as ModelKey)}
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '8px',
                  fontSize: '14px',
                  border: '1px solid #ddd',
                  borderRadius: '4px'
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
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                Number of Turns:
              </label>
              <select
                value={turns}
                onChange={(e) => setTurns(parseInt(e.target.value))}
                disabled={loading}
                style={{
                  width: '100%',
                  padding: '8px',
                  fontSize: '14px',
                  border: '1px solid #ddd',
                  borderRadius: '4px'
                }}
              >
                {[1, 2, 3, 4, 5, 6].map(n => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>
          </div>

          {!showApiKeys && (
            <div style={{
              padding: '12px',
              background: '#f9fafb',
              border: '1px solid #e5e7eb',
              borderRadius: '4px',
              marginBottom: '20px'
            }}>
              <p style={{ fontSize: '13px', fontWeight: 'bold', marginBottom: '8px', color: '#374151' }}>
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
          )}

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
                color: '#0070f3',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontSize: '14px',
                textDecoration: 'underline',
                padding: 0
              }}
            >
              {showApiKeys ? 'Hide' : 'Show'} API Keys (optional - for unlimited usage)
            </button>

            {showApiKeys && (
              <div style={{
                marginTop: '15px',
                padding: '15px',
                background: '#f5f5f5',
                borderRadius: '4px'
              }}>
                <p style={{ fontSize: '13px', color: '#666', marginBottom: '10px' }}>
                  You get {rateLimit} free uses per model per day. To unlock unlimited usage, add your own API keys:
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
                      fontSize: '14px',
                      border: '1px solid #ddd',
                      borderRadius: '4px'
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
                      fontSize: '14px',
                      border: '1px solid #ddd',
                      borderRadius: '4px'
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
                      fontSize: '14px',
                      border: '1px solid #ddd',
                      borderRadius: '4px'
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
                      fontSize: '14px',
                      border: '1px solid #ddd',
                      borderRadius: '4px'
                    }}
                  />
                </div>
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={loading || (usingServerKeys && allServerModelsExhausted)}
            style={{
              width: '100%',
              padding: '12px',
              fontSize: '16px',
              fontWeight: 'bold',
              color: 'white',
              background: loading || (usingServerKeys && allServerModelsExhausted) ? '#ccc' : '#0070f3',
              border: 'none',
              borderRadius: '4px',
              cursor: loading || (usingServerKeys && allServerModelsExhausted) ? 'not-allowed' : 'pointer'
            }}
          >
            {loading ? 'Running Debate...' : 'Start Debate'}
          </button>
        </form>

        {loading && (
          <div style={{ marginBottom: '20px' }}>
            <div style={{
              width: '100%',
              height: '30px',
              background: '#e5e7eb',
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
            <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'center', color: '#666' }}>
              <div style={{ textAlign: 'left', fontSize: '14px' }}>
                {progressMessage.primary && (
                  <p style={{ margin: 0 }}>{progressMessage.primary}</p>
                )}
                {progressMessage.secondary && (
                  <p style={{ margin: '4px 0 0 0' }}>{progressMessage.secondary}</p>
                )}
              </div>
            </div>
          </div>
        )}

        {error && (
          <div style={{
            padding: '15px',
            background: '#fee',
            border: '1px solid #fcc',
            borderRadius: '4px',
            marginBottom: '20px',
            color: '#c00'
          }}>
            <strong>Error:</strong> {error}
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
                    <p><strong>Source:</strong> <a href={turn.url} target="_blank" rel="noopener noreferrer" style={{ color: '#0070f3' }}>{turn.url}</a></p>
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
            align-items: stretch;
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
            padding: 20px;
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
            color: #0070f3;
            text-decoration: none;
          }

          .hero-description a:hover,
          .hero-description a:focus {
            text-decoration: underline;
          }

          .hero-image {
            max-width: clamp(320px, 38vw, 470px);
            width: 100%;
            margin: 0 auto;
            order: 1;
          }

          .hero-image picture {
            display: block;
            width: min(100%, clamp(320px, 36vw, 450px));
            margin: 0 auto;
          }

          .hero-image img {
            width: 100%;
            height: auto;
            max-height: clamp(230px, 26vw, 300px);
            display: block;
            border-radius: 16px;
            box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
            aspect-ratio: 2400 / 1260;
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
      </div>
    </>
  );
}
