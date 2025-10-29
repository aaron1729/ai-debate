# Claude.md - Implementation Context

This file provides implementation details and design decisions for the AI Debate System to help future development.

## Project Overview

An adversarial truth-seeking system that uses AI debate to evaluate factual claims. Two AI agents argue opposing sides while a judge evaluates the evidence presented.

**Core Hypothesis**: As debate length increases, verdicts should stabilize toward truth. Misleading arguments are more likely to succeed in shorter debates.

## Current Status

### Deployment Status
- ✅ **CLI working**: Python command-line interface fully functional
- ✅ **Web UI working locally**: Next.js app runs on localhost with all features
- ❌ **NOT deployed to Vercel**: Rate limiting logic needs to be fixed before deployment

### Implemented Features

**Core Debate System:**
- ✅ CLI script with configurable turn counts (1-6)
- ✅ Web UI with same debate functionality
- ✅ Multi-model support: Claude Sonnet 4.5, GPT-4, Gemini 2.5 Flash, Grok 3
- ✅ Judge using Paul Graham's disagreement hierarchy (DH0-DH6)
- ✅ Structured refusal handling (models can refuse in JSON format)
- ✅ Proper API error handling vs refusal detection
- ✅ Debate shortening when refusals occur
- ✅ Shared message templates between CLI and UI (shared/messages.json)

**Web Features:**
- ✅ Next.js 14 with TypeScript
- ✅ Real-time progress tracking during debates
- ✅ Turn-by-turn result display with animations
- ✅ Optional user-provided API keys (stored in browser only)
- ✅ Server-side API keys for free tier
- ⚠️ **PARTIAL**: Per-model rate limiting with Upstash Redis (UI refresh bug exists)

**Rate Limiting (Partially Working):**
- ✅ Upstash Redis integration
- ✅ Sliding window rate limiting (24 hour window)
- ✅ Admin IP privileges via environment variables
- ✅ Per-model tracking (Claude, GPT-4, Gemini, Grok)
- ✅ Localhost detection for development (treated as admin)
- ❌ **BUG**: Rate limit counts reset to max on page refresh (see Known Issues)

**Test Data Integration:**
- ✅ Google Fact Check Tools API integration
- ✅ Script to fetch real fact-checked claims (fetch_claims.py)
- ✅ Three test datasets: recent politics (6 claims), health (50 claims), climate (50 claims)
- ✅ API key authentication (simpler than service accounts)
- ✅ Documentation for fetching custom datasets

### Not Yet Implemented
- ⏳ Web scraping/verification of cited sources
- ⏳ Persistent storage/database for debate history
- ⏳ Source credibility weighting
- ⏳ Multiple judges ("mixture of experts")
- ⏳ RL policy learning
- ⏳ Public deployment on Vercel

## Architecture

### File Structure
```
/
├── debate.py                      # Python CLI script
├── fetch_claims.py                # Fetch claims from Google Fact Check API
├── requirements.txt               # Python dependencies
├── package.json                   # Node.js dependencies
├── pages/
│   ├── index.tsx                  # Main web UI component
│   └── api/
│       ├── debate.ts             # Debate API endpoint with rate limiting
│       ├── check-rate-limit.ts   # Rate limit checker (has bug)
│       ├── check-usage.ts        # Debug endpoint for Redis inspection
│       ├── list-redis-keys.ts    # Debug endpoint for Redis keys
│       └── get-remaining.ts      # Debug endpoint
├── lib/
│   └── debate-engine.ts          # TypeScript debate logic (shared with API)
├── shared/
│   └── messages.json             # Progress messages (shared between CLI & UI)
├── claims_recent_30days.json      # Test data: 6 recent political claims
├── claims_historical_health_50.json   # Test data: 50 health claims
├── claims_historical_climate_50.json  # Test data: 50 climate claims
├── docs/
│   ├── CLAUDE.md                 # This file - implementation context
│   ├── DEPLOYMENT.md             # Vercel deployment guide
│   └── FACTCHECK_SETUP.md        # Google Fact Check API setup guide
├── .env                          # Environment variables (gitignored)
├── .env.example                  # Environment variable template
└── README.md                     # Project vision and roadmap
```

### Core Components

#### Python CLI (debate.py)

**1. Debater Class** (debate.py:20-190)
- Takes a position ("pro" or "con")
- Generates arguments with citations (URL, quote, context, argument)
- Can explicitly refuse using structured JSON format
- System prompt emphasizes participation while allowing refusal as last resort

**2. Judge Class** (debate.py:193-234)
- Reviews full debate transcript (including refusals)
- Assigns one of 4 verdicts: supported/contradicted/misleading/needs more evidence
- Provides brief explanation

**3. Debate Orchestrator** (run_debate function, debate.py:231-316)
- Alternates between Pro and Con for T turns
- Filters refusals from debate history shown to opponents
- Shortens debate after first refusal (allows one counter-argument)
- Passes complete transcript to judge

#### TypeScript Web App

**1. Frontend** (pages/index.tsx)
- React component with real-time progress tracking
- Displays rate limits per model
- Handles user-provided API keys (browser storage only)
- Progressive result display with animations
- useEffect hook fetches rate limits on page load

**2. API Route** (pages/api/debate.ts)
- Validates input (claim, turns, models)
- Determines if using server keys or user keys
- **Rate limiting logic**:
  - Creates single Ratelimit instance with ADMIN_RATE_LIMIT (500)
  - Tracks all usage in unified Redis database
  - Calculates: `used = ADMIN_RATE_LIMIT - remaining`
  - Checks: `if (used >= userLimit)` where userLimit is 5 or 500
  - Returns: `actualRemaining = userLimit - used`
- Calls `runDebate()` from lib/debate-engine.ts
- Returns JSON with debate history and verdict

**3. Debate Engine** (lib/debate-engine.ts)
- TypeScript implementation of debate logic
- Supports multiple LLM providers (Anthropic, OpenAI, Google, xAI)
- Model configuration with API endpoints and formatting
- Shared between API routes

**4. Rate Limit Checker** (pages/api/check-rate-limit.ts)
- Called on page load to show initial rate limits
- Uses Lua script to read Redis sorted sets without consuming tokens
- ⚠️ **BUG**: Not correctly persisting/reading usage across refreshes

### Test Data Integration (Google Fact Check Tools API)

**Purpose**: Fetch real fact-checked claims to test the debate system's accuracy by comparing verdicts with professional fact-checker ratings.

**Implementation** (fetch_claims.py):
- Uses Google Fact Check Tools API with API key authentication
- **No service account needed** (API key only for `claims:search` endpoint)
- Fetches claims with customizable parameters: query, date range, language
- Saves structured JSON with claim text, claimant, fact-checker ratings, and source URLs

**Authentication Discovery**:
- Initially tried service account approach (doesn't work for read-only endpoint)
- Service accounts are only for `pages.*` write endpoints (creating ClaimReview pages)
- The `claims:search` endpoint requires API key authentication
- Can reuse existing `GOOGLE_API_KEY` (same key used for Gemini)

**API Parameters** (fetch_claims.py:12-61):
- `query`: Required search term (e.g., "health", "climate", "the")
- `languageCode`: Recommended ('en' for English results)
- `maxAgeDays`: Time range for claims (default 30, can go up to 365+)
- `pageSize`: Results per page (keep at 10-20, larger values trigger errors)
- Automatic pagination handling with exponential backoff

**Current Test Datasets**:

1. **claims_recent_30days.json** (6 claims)
   - Recent political claims from last 30 days
   - Query: "the" (broad search)
   - Fetched: 2025-10-29

2. **claims_historical_health_50.json** (50 claims)
   - Health-related claims from last year
   - Query: "health"
   - Date range: 365 days
   - Diverse fact-checkers (AFP, PolitiFact, FactCheck.org, etc.)

3. **claims_historical_climate_50.json** (50 claims)
   - Climate-related claims from last year
   - Query: "climate"
   - Date range: 365 days
   - Mix of environmental and scientific claims

**Data Structure**:
```json
{
  "fetched_at": "2025-10-29T12:34:56",
  "count": 50,
  "claims": [
    {
      "text": "Claim text here",
      "claimant": "Source or person",
      "claimDate": "2025-10-15T00:00:00Z",
      "claimReview": [
        {
          "publisher": {"name": "AFP Fact Check", "site": "factcheck.afp.com"},
          "url": "https://factcheck.afp.com/...",
          "textualRating": "False",
          "reviewDate": "2025-10-20T00:00:00Z"
        }
      ]
    }
  ]
}
```

**Common Ratings**:
- False, Mostly False, Partly False
- True, Mostly True, Partly True
- Misleading, Needs Context, Unproven
- Mix of True and False (for complex claims)

**Usage for Testing**:
1. Load claims from JSON files
2. Run debates on each claim using `debate.py`
3. Map fact-checker ratings to debate verdicts:
   - "False" → should get "contradicted" or "misleading"
   - "True" → should get "supported"
   - "Misleading/Needs Context" → should get "misleading" or "needs more evidence"
4. Analyze agreement rates and identify patterns/biases

**Key Learning**: Service account confusion wasted significant time. The API documentation is unclear about authentication methods. API key is simpler and correct for read-only access.

**See**: docs/FACTCHECK_SETUP.md for complete setup guide and troubleshooting.

### Environment Variables

Required for web deployment:
```bash
# API Keys for free tier (server-side only)
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx
GOOGLE_API_KEY=AIzaSyxxxxx
XAI_API_KEY=xai-xxxxx

# Upstash Redis for rate limiting (required)
UPSTASH_REDIS_REST_URL=https://xxx.upstash.io
UPSTASH_REDIS_REST_TOKEN=AXXXxxx

# Admin rate limiting (optional)
ADMIN_IP=your.public.ip.here          # Gets ADMIN_RATE_LIMIT
ADMIN_RATE_LIMIT=500                  # Default: 500 uses/model/day

# Notes:
# - Localhost (::1, 127.0.0.1) treated as admin when ADMIN_IP is set
# - Non-admin IPs get 5 uses/model/day (DEFAULT_RATE_LIMIT)
# - Rate limits use 24-hour sliding window
```

## Key Design Decisions

### 1. Structured Refusals (Not Errors)

**Problem**: Models sometimes refuse to argue controversial positions. Initially treated as errors.

**Solution**: Allow explicit refusal in JSON format:
```json
{"refused": true, "reason": "explanation"}
```

**Benefits**:
- Refusals become data about model behavior/biases
- Clean separation from API errors or malformed responses
- Can study which models refuse which claims

**Implementation**: See debate.py:165-176 and lib/debate-engine.ts

### 2. Debate History Filtering

**Key Insight**: When one side refuses, opponent shouldn't know about it.

**Implementation** (debate.py:108-119, lib/debate-engine.ts):
- Refusals are filtered out when building debate history for opponent
- Opponent sees empty history and argues as if going first
- This prevents "arguing against a refusal" confusion

**Why**: Preserves adversarial structure even with asymmetric participation.

### 3. Unified Rate Limiting Strategy

**Problem**: Creating separate rate limiter instances for different limits (5 vs 500) tracked usage separately in Redis.

**Solution** (pages/api/debate.ts:15-20, 72-92):
- Use ONE rate limiter configured with maximum limit (ADMIN_RATE_LIMIT = 500)
- Track all usage in the same Redis database
- Calculate used: `used = 500 - remaining`
- Check against user's actual limit: `if (used >= rateLimit)` (5 or 500)
- Return accurate remaining: `actualRemaining = rateLimit - used`

**Benefits**:
- All usage tracked in unified database
- Admin and non-admin users share same tracking system
- Changing limits doesn't create separate tracking buckets

**Current Issue**: See Known Issues below.

### 4. Shared Message Templates

**Implementation** (shared/messages.json):
- Single JSON file with all progress messages
- Used by both Python CLI and TypeScript UI
- Template variables: `{turns}`, `{turn}`, `{total_turns}`, `{model_name}`

**Why**: Single source of truth prevents UI/CLI message drift.

### 5. Paul Graham's Disagreement Hierarchy Integration

**Judge Prompt** (lib/debate-engine.ts and debate.py):
- References DH0 (name-calling) through DH6 (refuting central point)
- Instructs judge to evaluate arguments on this scale
- **Important**: Numbers are only in system prompt, not shown to models
- Prevents models from gaming the system by explicitly targeting DH levels

### 6. Admin IP with Localhost Detection

**Challenge**: During local development, IP is `::1` or `127.0.0.1`, not public IP.

**Solution** (pages/api/debate.ts:58-62):
```typescript
const isLocalhost = identifier === '::1' || identifier === '127.0.0.1' || identifier === '::ffff:127.0.0.1';
const isAdmin = ADMIN_IP && (identifier === ADMIN_IP || isLocalhost);
```

**Result**: Admin privileges work during `npm run dev` locally.

## Model Configuration

### Supported Models

| Model | Provider | Key | ID |
|-------|----------|-----|-----|
| Claude Sonnet 4.5 | Anthropic | `ANTHROPIC_API_KEY` | `claude-sonnet-4-20250514` |
| GPT-4 | OpenAI | `OPENAI_API_KEY` | `gpt-4o` |
| Gemini 2.5 Flash | Google | `GOOGLE_API_KEY` | `gemini-2.5-flash-latest-exp-0827` |
| Grok 3 | xAI | `XAI_API_KEY` | `grok-3-latest` |

**Removed**: GPT-3.5 Turbo (kept one model per AI lab)

### Adding New Models

1. Add to `MODELS` object in lib/debate-engine.ts
2. Add API key to .env and .env.example
3. Implement provider-specific client in lib/debate-engine.ts
4. Handle provider-specific response formats
5. Test refusal behavior (varies significantly by model)

## Known Issues

### 🐛 CRITICAL: Rate Limit Reset on Page Refresh

**Status**: Not fixed, blocking Vercel deployment

**Symptom**:
- User runs debate: Count decrements correctly (e.g., 500 → 499)
- User refreshes page: Count resets to max (499 → 500)

**Root Cause**:
- The `/api/check-rate-limit` endpoint uses Lua script to read Redis sorted sets
- Script may not be reading the same keys that the Ratelimit library writes to
- Upstash Ratelimit uses complex internal key structure (events, buckets, etc.)

**Attempted Fixes**:
1. ❌ Direct `zcount` query on `@upstash/ratelimit:{identifier}:{model}`
2. ❌ Lua script with `zremrangebyscore` + `zcard`
3. ❌ Creating separate ratelimiter instance to call `limit()` (consumes tokens)

**Why It's Hard**:
- Calling `ratelimiter.limit()` consumes a token (can't use for read-only checks)
- Upstash Ratelimit library doesn't expose `getRemaining()` method
- Internal Redis key structure is complex (sorted sets + analytics events)
- Need to read the exact keys the library writes to, in the exact format

**Next Steps to Try**:
1. Examine Upstash Ratelimit source code to understand exact key format
2. Use Redis SCAN to find all keys matching pattern and debug structure
3. Consider using Upstash Ratelimit's analytics API if available
4. Alternative: Accept that page load shows max limit, only update after first debate
5. Alternative: Store usage client-side in localStorage (less secure)

**Impact**:
- Cannot deploy to Vercel until fixed
- Users see misleading "500/500" on page load even after using quota
- Functional for single-session use, but bad UX for returning users

### Other Minor Issues

**Progress Text During API Wait**:
- ✅ FIXED: Now shows "Starting debate... Please wait..." during API call
- Previously stuck on "Starting debate..." with no updates

**Turn Counter Bug**:
- ✅ FIXED: Was showing "Turn 11/2..." due to progress interval incrementing turn counter
- Now only updates percentage during wait, turn numbers shown when displaying results

## Testing Guidance

### Local Development

```bash
# Python CLI
python debate.py

# Web UI
npm install
npm run dev
# Visit http://localhost:3000
```

### Good Test Claims

**Basic factual claims** (should work well):
- "Electric vehicles produce less CO2 than gas cars over their lifetime"
- "Coffee consumption is associated with health benefits"
- "apples are better than bananas" (subjective but debatable)

**Misleading claims** (should get "misleading" verdict):
- "Vaccines contain toxic chemicals like formaldehyde"
- "More people die from falling out of bed than from terrorism"
- "95% of people who use heroin started with marijuana"

**Avoid**:
- Direct character attacks on named living individuals (likely refused)

### Expected Behavior

**Normal debate**:
1. Pro argues → Con argues → repeat for T turns
2. Judge evaluates and assigns verdict
3. Clean output with sources and reasoning

**With refusal**:
1. One side refuses (e.g., Pro refuses turn 1)
2. Con makes one counter-argument (turn 1)
3. Debate stops, goes to judge
4. Output shows refusal + counter-argument + verdict

**API error**:
- Clear error message indicating API issue
- Exit immediately (can't continue without API)

## Deployment (Not Yet Done)

### Prerequisites
1. ✅ Fix rate limit refresh bug
2. ✅ Test thoroughly with multiple models
3. ✅ Verify all environment variables work in production
4. ✅ Ensure cost limits are appropriate

### Deployment Steps (See DEPLOYMENT.md)
1. Create Upstash Redis database
2. Push code to GitHub
3. Import to Vercel
4. Add environment variables
5. Deploy
6. Test rate limiting in production
7. Monitor costs and usage

**Current Blocker**: Rate limit refresh bug must be fixed first.

## Development Tips

### Debugging Rate Limiting

**Check Redis data**:
```bash
curl http://localhost:3000/api/list-redis-keys | python3 -m json.tool
curl http://localhost:3000/api/check-usage | python3 -m json.tool
```

**Monitor rate limit headers**:
- Check browser Network tab for `X-RateLimit-Models` header
- Contains remaining counts after each debate

**Test different IPs**:
- Localhost: Should get ADMIN_RATE_LIMIT (500)
- Other IPs: Should get DEFAULT_RATE_LIMIT (5)
- Check console logs for `[Rate Limit] IP: ...` debug output

### Adding New Features

**To add a new LLM provider**:
1. Add to `MODELS` object in lib/debate-engine.ts
2. Create API client initialization
3. Implement response parsing (JSON extraction, error handling)
4. Test refusal behavior (may differ significantly)
5. Update .env.example with new API key

**To save debate data**:
1. Create database schema (timestamp, models, claim, turns, verdict, transcript)
2. Add database writes after verdict in pages/api/debate.ts
3. Consider privacy implications of storing API responses
4. Add UI for viewing past debates

**To verify citations**:
1. Add URL fetching in debate engine before returning arguments
2. Check if quote appears in fetched content
3. Flag suspicious citations in debate history
4. Handle errors gracefully (paywalls, 404s, etc.)

### Common Issues

**"No JSON found in response"**:
- Model returned plain text instead of JSON
- Check if model is refusing (should use structured format now)
- May indicate prompt confusion - review system prompt

**Both sides refuse**:
- Claim may be too controversial for current model
- Try rephrasing as idea/policy rather than person
- Consider testing with different model

**Rate limit shows 500/500 after using quota**:
- This is the known bug - see Known Issues section
- Workaround: Check actual behavior by trying to run debate

**TypeScript build errors after model changes**:
- Run `npm run build` to check for type errors
- Ensure ModelKey type matches MODELS object keys

## Future Considerations

### When Rate Limiting is Fixed

**Data to collect**:
- Usage patterns by model
- Refusal rates by model and claim type
- Cost per debate by model
- Popular vs unpopular models

**Monitoring**:
- Set up Vercel analytics
- Monitor Upstash Redis usage
- Track API costs per provider
- Alert on unusual usage patterns

### When Adding Persistent Storage

**What to store**:
- Full debate transcripts (including refusals)
- Metadata: models used, timestamp, turn count, verdict
- User-provided claim + any ground truth labels
- Source URLs and quotes (for future verification)
- User feedback on verdict quality

**Analysis possibilities**:
- First-mover advantage/disadvantage
- Verdict stability vs turn count (test core hypothesis)
- Model-specific biases in refusals
- Source quality correlation with verdicts
- Cross-model agreement rates

### When Adding Source Verification

**Challenges**:
- Paywalls, authentication, dynamic content
- Phishing/malicious URLs
- Rate limiting from source sites
- Computational cost of fetching many URLs

**Recommendation**:
- Start with URL validation (reachable, HTTPS)
- Add sampling (verify subset of citations)
- Cache fetched content to reduce redundant requests
- Consider using dedicated scraping service/API

## API Key Management

**Current approach**:
- Server keys in .env (never exposed to client)
- User keys optional (stored in browser only, sent with each request)
- User keys bypass rate limiting

**Production considerations**:
- Monitor API costs per provider
- Implement retry logic with exponential backoff
- Add cost tracking (tokens used per debate)
- Consider capping free tier usage per month

## Contributing

When modifying the system, please:
1. Update this file if architecture changes
2. Test with various claim types (factual, misleading, controversial)
3. Check both CLI and web UI
4. Verify error messages are clear and actionable
5. Test rate limiting behavior
6. Run `npm run build` to check for TypeScript errors
7. Consider implications for research hypothesis

## Resources

- Anthropic API docs: https://docs.anthropic.com/
- OpenAI API docs: https://platform.openai.com/docs
- Google AI docs: https://ai.google.dev/docs
- xAI API docs: https://docs.x.ai/
- Upstash Redis docs: https://docs.upstash.com/redis
- Upstash Ratelimit docs: https://upstash.com/docs/oss/sdks/ts/ratelimit/overview
- Next.js docs: https://nextjs.org/docs
- Vercel deployment: https://vercel.com/docs
