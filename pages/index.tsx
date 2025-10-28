import { useState } from 'react';
import Head from 'next/head';
import { MODELS, ModelKey, DebateResult } from '../lib/debate-engine';

export default function Home() {
  const [claim, setClaim] = useState('');
  const [turns, setTurns] = useState(2);
  const [proModel, setProModel] = useState<ModelKey>('claude');
  const [conModel, setConModel] = useState<ModelKey>('claude');
  const [judgeModel, setJudgeModel] = useState<ModelKey>('claude');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<DebateResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showApiKeys, setShowApiKeys] = useState(false);
  const [apiKeys, setApiKeys] = useState({
    anthropic: '',
    openai: '',
    google: '',
    xai: ''
  });
  const [rateLimitInfo, setRateLimitInfo] = useState<{
    remaining?: number;
    resetAt?: string;
  }>({});

  const modelKeys = Object.keys(MODELS) as ModelKey[];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

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

      // Extract rate limit headers
      const remaining = response.headers.get('X-RateLimit-Remaining');
      const reset = response.headers.get('X-RateLimit-Reset');
      if (remaining) {
        setRateLimitInfo({
          remaining: parseInt(remaining),
          resetAt: reset ? new Date(parseInt(reset) * 1000).toISOString() : undefined
        });
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || data.error || 'Failed to run debate');
      }

      setResult(data);
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
        <p style={{ textAlign: 'center', color: '#666', marginBottom: '40px' }}>
          Adversarial truth-seeking through structured debates
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

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '15px', marginBottom: '20px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                Pro Model:
              </label>
              <select
                value={proModel}
                onChange={(e) => setProModel(e.target.value as ModelKey)}
                style={{
                  width: '100%',
                  padding: '8px',
                  fontSize: '14px',
                  border: '1px solid #ddd',
                  borderRadius: '4px'
                }}
              >
                {modelKeys.map(key => (
                  <option key={key} value={key}>{MODELS[key].name}</option>
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
                style={{
                  width: '100%',
                  padding: '8px',
                  fontSize: '14px',
                  border: '1px solid #ddd',
                  borderRadius: '4px'
                }}
              >
                {modelKeys.map(key => (
                  <option key={key} value={key}>{MODELS[key].name}</option>
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
                style={{
                  width: '100%',
                  padding: '8px',
                  fontSize: '14px',
                  border: '1px solid #ddd',
                  borderRadius: '4px'
                }}
              >
                {modelKeys.map(key => (
                  <option key={key} value={key}>{MODELS[key].name}</option>
                ))}
              </select>
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: 'bold' }}>
                Number of Turns:
              </label>
              <input
                type="number"
                value={turns}
                onChange={(e) => setTurns(parseInt(e.target.value))}
                min="1"
                max="5"
                required
                style={{
                  width: '100%',
                  padding: '8px',
                  fontSize: '14px',
                  border: '1px solid #ddd',
                  borderRadius: '4px'
                }}
              />
            </div>
          </div>

          <div style={{ marginBottom: '20px' }}>
            <button
              type="button"
              onClick={() => setShowApiKeys(!showApiKeys)}
              style={{
                background: 'none',
                border: 'none',
                color: '#0070f3',
                cursor: 'pointer',
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
                  You get 5 free debates per day. To unlock unlimited usage, add your own API keys:
                </p>
                <div style={{ display: 'grid', gap: '10px' }}>
                  <input
                    type="password"
                    placeholder="Anthropic API Key (optional)"
                    value={apiKeys.anthropic}
                    onChange={(e) => setApiKeys({ ...apiKeys, anthropic: e.target.value })}
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

          {rateLimitInfo.remaining !== undefined && !showApiKeys && (
            <p style={{ fontSize: '13px', color: '#666', marginBottom: '15px' }}>
              Free debates remaining today: {rateLimitInfo.remaining}/5
            </p>
          )}

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

        {result && (
          <div>
            <h2 style={{ marginBottom: '10px' }}>Debate Results</h2>

            <div style={{
              padding: '15px',
              background: '#f0f8ff',
              border: '1px solid #add8e6',
              borderRadius: '4px',
              marginBottom: '20px'
            }}>
              <h3 style={{ marginTop: 0 }}>Claim:</h3>
              <p style={{ fontSize: '16px', marginBottom: '10px' }}>{result.claim}</p>

              <h3>Verdict: {result.verdict.verdict.toUpperCase()}</h3>
              <p>{result.verdict.explanation}</p>

              <p style={{ fontSize: '13px', color: '#666', marginTop: '10px' }}>
                <strong>Models:</strong> Pro: {result.models.pro} | Con: {result.models.con} | Judge: {result.models.judge}
              </p>
            </div>

            <h3>Debate Transcript:</h3>
            {result.debate_history.map((turn, i) => (
              <div
                key={i}
                style={{
                  padding: '15px',
                  marginBottom: '15px',
                  background: turn.position === 'pro' ? '#e8f5e9' : '#ffebee',
                  border: turn.position === 'pro' ? '1px solid #a5d6a7' : '1px solid #ef9a9a',
                  borderRadius: '4px'
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
                    <p><strong>Source:</strong> <a href={turn.url} target="_blank" rel="noopener noreferrer">{turn.url}</a></p>
                    <p><strong>Quote:</strong> "{turn.quote}"</p>
                    <p><strong>Context:</strong> {turn.context}</p>
                    <p><strong>Argument:</strong> {turn.argument}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
