import { useState, useEffect } from 'react';
import Head from 'next/head';
import { MODELS, ModelKey, DebateResult, DebateTurn } from '../lib/debate-engine';
import messages from '../shared/messages.json';

export default function Home() {
  const [claim, setClaim] = useState('');
  const [turns, setTurns] = useState(2);
  const [proModel, setProModel] = useState<ModelKey>('claude');
  const [conModel, setConModel] = useState<ModelKey>('claude');
  const [judgeModel, setJudgeModel] = useState<ModelKey>('claude');
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressText, setProgressText] = useState('');
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
  const [modelLimits, setModelLimits] = useState<Record<string, { remaining: number; limit?: number }>>({});
  const [hasLoadedLimits, setHasLoadedLimits] = useState(false);
  const [rateLimit, setRateLimit] = useState(5);

  const modelKeys = Object.keys(MODELS) as ModelKey[];

  // Fetch initial rate limit and usage on page load
  useEffect(() => {
    const fetchRateLimit = async () => {
      try {
        const response = await fetch('/api/check-rate-limit');
        if (response.ok) {
          const data = await response.json();
          setRateLimit(data.limit);

          // Set model limits from the API response
          if (data.modelLimits) {
            setModelLimits(data.modelLimits);
            setHasLoadedLimits(true);
          }
        }
      } catch (err) {
        // If check fails, keep default of 5
        console.error('Failed to check rate limit:', err);
      }
    };
    fetchRateLimit();
  }, []);

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
    setProgress(0);
    setProgressText(messages.start.replace('{turns}', turns.toString()) + ' Please wait...');

    try {
      // Determine which API keys to send
      const userApiKeys = showApiKeys && (
        apiKeys.anthropic || apiKeys.openai || apiKeys.google || apiKeys.xai
      ) ? {
        ...(apiKeys.anthropic && { anthropic: apiKeys.anthropic }),
        ...(apiKeys.openai && { openai: apiKeys.openai }),
        ...(apiKeys.google && { google: apiKeys.google }),
        ...(apiKeys.xai && { xai: apiKeys.xai })
      } : undefined;

      const totalSteps = turns * 2 + 1; // Pro + Con per turn + Judge
      let currentStep = 0;

      // Update progress as we wait for the response
      const progressInterval = setInterval(() => {
        // Simulate progress up to 90% while waiting
        setProgress(prev => Math.min(prev + 2, 90));
      }, 200);

      const response = await fetch('/api/debate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          claim,
          turns,
          proModel,
          conModel,
          judgeModel,
          userApiKeys
        })
      });

      clearInterval(progressInterval);

      // Extract rate limit headers
      const rateLimitModels = response.headers.get('X-RateLimit-Models');
      if (rateLimitModels) {
        const limits = JSON.parse(rateLimitModels);
        // Get the rate limit from first model (all models share the same limit per IP)
        const firstLimit = Object.values(limits)[0] as any;
        const totalLimit = firstLimit?.limit || 5;
        setRateLimit(totalLimit);

        // Ensure all models are shown with their limits
        const allLimits: Record<string, { remaining: number; limit?: number }> = {};
        modelKeys.forEach(key => {
          allLimits[key] = limits[key] || { remaining: totalLimit, limit: totalLimit };
        });
        setModelLimits(allLimits);
        setHasLoadedLimits(true);
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || data.error || 'Failed to run debate');
      }

      // Simulate progressive display (since we get all data at once)
      // In a real streaming implementation, this would happen naturally
      for (let i = 0; i < data.debate_history.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 300));
        setDebateHistory(prev => [...prev, data.debate_history[i]]);
        currentStep++;
        setProgress(90 + (currentStep / totalSteps) * 8); // 90-98%

        const turnNum = Math.floor(i / 2) + 1;
        const position = data.debate_history[i].position;
        const model = data.debate_history[i].model;

        // Format: "Turn {turn}/{total_turns}... {Side} side ({model}) is arguing..."
        const turnMsg = messages.turn
          .replace('{turn}', turnNum.toString())
          .replace('{total_turns}', turns.toString());
        const sideMsg = messages[position === 'pro' ? 'pro_turn' : 'con_turn']
          .replace('{model_name}', model);
        setProgressText(`${turnMsg}\n${sideMsg}`);
      }

      const judgeMsg = messages.judge_deliberating.replace('{model_name}', MODELS[judgeModel].name);
      setProgressText(judgeMsg);
      setProgress(98);
      await new Promise(resolve => setTimeout(resolve, 500));
      setVerdict(data.verdict);
      setProgress(100);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <Head>
        <title>AI Debate System</title>
        <meta name="description" content="Adversarial truth-seeking through structured AI debates" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <div style={{
        maxWidth: '1200px',
        margin: '0 auto',
        padding: '20px',
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}>
        <h1 style={{ textAlign: 'center', marginBottom: '10px' }}>AI Debate System</h1>
        <p style={{ textAlign: 'center', color: '#666', marginBottom: '10px' }}>
          Adversarial truth-seeking through structured debates
        </p>
        <p style={{ textAlign: 'center', fontSize: '14px', color: '#888', marginBottom: '5px' }}>
          A modernization of <a href="https://arxiv.org/abs/1805.00899" target="_blank" rel="noopener noreferrer" style={{ color: '#0070f3', textDecoration: 'none' }}>AI safety via debate</a> (Irving et al., 2018)
        </p>
        <p style={{ textAlign: 'center', fontSize: '13px', color: '#999', marginBottom: '40px' }}>
          Judge evaluation based on <a href="http://www.paulgraham.com/disagree.html" target="_blank" rel="noopener noreferrer" style={{ color: '#0070f3', textDecoration: 'none' }}>Paul Graham&apos;s disagreement hierarchy</a>
        </p>

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
                {modelKeys.map(key => (
                  <option
                    key={key}
                    value={key}
                    disabled={modelLimits[key]?.remaining === 0}
                    style={{
                      color: modelLimits[key]?.remaining === 0 ? '#ccc' : 'inherit'
                    }}
                  >
                    {MODELS[key].name}
                  </option>
                ))}
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
                {modelKeys.map(key => (
                  <option
                    key={key}
                    value={key}
                    disabled={modelLimits[key]?.remaining === 0}
                    style={{
                      color: modelLimits[key]?.remaining === 0 ? '#ccc' : 'inherit'
                    }}
                  >
                    {MODELS[key].name}
                  </option>
                ))}
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
                {modelKeys.map(key => (
                  <option
                    key={key}
                    value={key}
                    disabled={modelLimits[key]?.remaining === 0}
                    style={{
                      color: modelLimits[key]?.remaining === 0 ? '#ccc' : 'inherit'
                    }}
                  >
                    {MODELS[key].name}
                  </option>
                ))}
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
                  const remaining = modelLimits[key]?.remaining ?? rateLimit;
                  return (
                    <div key={key} style={{ fontSize: '12px', color: remaining === 0 ? '#ef4444' : '#6b7280' }}>
                      <strong>{MODELS[key].name}:</strong> {remaining}/{rateLimit}
                    </div>
                  );
                })}
              </div>
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
            disabled={loading}
            style={{
              width: '100%',
              padding: '12px',
              fontSize: '16px',
              fontWeight: 'bold',
              color: 'white',
              background: loading ? '#ccc' : '#0070f3',
              border: 'none',
              borderRadius: '4px',
              cursor: loading ? 'not-allowed' : 'pointer'
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
            <p style={{ textAlign: 'center', marginTop: '8px', color: '#666', fontSize: '14px', whiteSpace: 'pre-line' }}>
              {progressText}
            </p>
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
