# Claude.md - Implementation Context

This file provides comprehensive implementation details and design decisions for the AI Debates system to help future development.

## Project Overview

An adversarial truth-seeking system that uses AI debate to evaluate factual claims. Two AI agents argue opposing sides while a judge evaluates the evidence presented.

**Core Hypothesis**: As debate length increases, verdicts should stabilize toward truth. Misleading arguments are more likely to succeed in shorter debates.

This implementation comprises:
- An end-to-end pipeline for running automated debates with two LLM debaters and an LLM judge
- The pipeline is deployed as a web app at https://ai-debate-4-u.vercel.app/
- Sourced, cleaned, and verified datasets from multiple sources (Google Fact Check API, GPT-5 generation, debate podcasts)
- 280+ debates run across various configurations with comprehensive analysis

## Current Status

### Deployment Status
- ✅ **CLI working**: Python command-line interface fully functional
- ✅ **Web UI working locally**: Next.js app runs on localhost with all features
- ✅ **Deployed to Vercel**: Live at https://ai-debate-4-u.vercel.app/ with Upstash-backed rate limiting

### Implemented Features

**Core Debate System:**
- ✅ CLI script with configurable turn counts (1-6)
- ✅ Web UI with same debate functionality
- ✅ Multi-model support: Claude Sonnet 4.5, GPT-4, Gemini 2.5 Flash, Grok 3
- ✅ Judge using Paul Graham's disagreement hierarchy (DH0-DH6)
- ✅ Structured refusal handling (models can refuse in JSON format)
- ✅ Comprehensive API error handling with user-friendly messages
- ✅ Retry functionality for transient errors (overload, timeout, network)
- ✅ Debate shortening when refusals occur
- ✅ Shared message templates between CLI and UI (shared/messages.json)
- ✅ One-shot retries when debaters or judge return malformed JSON (Python CLI + TS engine)

**Web Features:**
- ✅ Next.js 14 with TypeScript
- ✅ Real-time progress tracking during debates
- ✅ Turn-by-turn result display with animations
- ✅ Optional user-provided API keys (stored in browser only)
- ✅ Server-side API keys for free tier
- ✅ Sample debate cards with adaptive model selection
- ✅ Responsive design (6 cards desktop, 2 cards mobile)
- ⚠️ **PARTIAL**: Per-model rate limiting with Upstash Redis (UI refresh bug exists)

**Rate Limiting (Partially Working):**
- ✅ Upstash Redis integration
- ✅ Sliding window rate limiting (24 hour window)
- ✅ Admin IP privileges via environment variables
- ✅ Per-model tracking (Claude, GPT-4, Gemini, Grok)
- ✅ Localhost detection for development (treated as admin)
- ✅ Redis-backed usage snapshots so the web UI shows true remaining counts across refreshes and restarts
- ✅ Global backstop of 200 free-tier requests per model per 24h (shared across all IPs)

**Test Data Integration:**
- ✅ Google Fact Check Tools API integration
- ✅ Script to fetch real fact-checked claims (fetch_claims.py)
- ✅ Three raw test datasets: recent politics (6 claims), health (50 claims), climate (50 claims)
- ✅ API key authentication (simpler than service accounts)
- ✅ Documentation for fetching custom datasets

**Data Processing Pipeline:**
- ✅ LLM-powered claim cleaning and standardization (process_factcheck_claims.py)
- ✅ URL fetching and content verification (verify_claims.py)
- ✅ Two-stage pipeline: process → verify
- ✅ Verdict mapping to debate system's 4 verdicts
- ✅ Temporal/geographical context enhancement
- ✅ Transparent modification logging
- ✅ Two verified datasets ready for testing: climate (48 claims), health (50 claims)
- ✅ Debate podcast data integration (process_debate_podcasts.py)
- ✅ Real-world debate motions from Munk Debates, Open To Debate, Soho Forum (37 motions)

### Not Yet Implemented
- ⏳ Verification of debaters' cited sources (URL fetching infrastructure exists, needs integration)
- ⏳ Persistent storage/database for debate history
- ⏳ Source credibility weighting
- ⏳ Multiple judges ("mixture of experts")
- ⏳ RL policy learning
- ⏳ Public deployment on Vercel

## Quick Start

### CLI Usage

1. Install dependencies:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Create `.env` file with your API keys:
```bash
cp .env.example .env
# Edit .env with your keys
```
- Add `PROMPT_LOG_IP_SALT` (for hashed IP logging) and other prompt-log settings if you want to exercise the new Redis logging pipeline. This path is freshly added and not yet tested end-to-end.

3. Run a debate:
```bash
python scripts/core/debate.py "Your claim here" --turns 2
```

Or run a single debate on debate motions:
```bash
python scripts/runners/run_single_debate.py --motion 0 --debater1 claude --debater2 grok
```

Options:
- `--turns`: Number of debate turns (default: 2)
- `--pro-model`: Model for pro side (claude/gpt4/gpt35/gemini/grok, default: claude)
- `--con-model`: Model for con side (default: claude)
- `--judge-model`: Model for judge (default: claude)

### Web Deployment

The web version is built with Next.js and can be deployed to Vercel.

1. Install Node.js dependencies:
```bash
npm install
```

2. Set up Upstash Redis for rate limiting:
   - Sign up at https://upstash.com/
   - Create a Redis database
   - Copy the REST URL and token to your `.env` file

3. Run locally:
```bash
npm run dev
```

4. Deploy to Vercel:
   - Push to GitHub
   - Import project in Vercel
   - Add environment variables in Vercel dashboard:
     - `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, etc. (for free tier)
     - `UPSTASH_REDIS_REST_URL` and `UPSTASH_REDIS_REST_TOKEN` (required)
      - `GLOBAL_MODEL_LIMIT` (optional global backstop, defaults to 200 free debates per model/day)
      - `SITE_URL` (public base URL, used for Open Graph/Twitter previews)

The web version includes:
- 5 free debates per IP per 24 hours
- Global backstop of 200 free debates per model per 24 hours (shared across all IPs)
- Option for users to provide their own API keys for unlimited usage
- Support for 4 models (Claude, GPT-4, Gemini, Grok)

## Architecture

### File Structure
```
/
├── scripts/                       # Python scripts organized by purpose
│   ├── core/
│   │   ├── debate.py             # Main debate engine (Python CLI)
│   │   └── experiment_store.py   # SQLite database abstraction
│   ├── runners/
│   │   ├── run_single_debate.py          # Run single debate on motion
│   │   ├── run_debate_motion_suite.py    # Run 4-config debate suite
│   │   ├── run_experiments.py            # Deterministic 2×8 experiment suite
│   │   └── run_experiments_randomize_all.py # Randomized sweeps with retry
│   ├── data_processing/
│   │   ├── fetch_claims.py               # Fetch from Google Fact Check API
│   │   ├── process_factcheck_claims.py   # Clean and standardize claims
│   │   ├── process_debate_podcasts.py    # Process podcast CSV to JSON
│   │   └── clean_debate_motions.py       # LLM-powered motion cleaning
│   ├── validation/
│   │   ├── verify_claims.py              # Verify claims with URL fetching
│   │   ├── validate_claims_json.py       # Validate claim JSON files
│   │   └── validate_experiment_json.py   # Validate experiment data
│   ├── analysis/
│   │   ├── query_experiments.py          # Query and analyze experiments
│   │   ├── judge_existing_debates.py     # Retrospectively judge debates
│   │   └── inspect_prompt_logs.py        # Inspect Redis prompt logs
│   └── utils/
│       ├── check_rate_limits.py          # Check/reset rate limit cache
│       └── test_anthropic_api.py         # Test API connection
├── pages/                         # Next.js pages
│   ├── index.tsx                  # Main web UI component
│   └── api/
│       ├── debate.ts              # Debate API endpoint with rate limiting
│       ├── check-rate-limit.ts    # Rate limit checker
│       ├── check-usage.ts         # Debug: Redis inspection
│       ├── list-redis-keys.ts     # Debug: Redis keys
│       └── get-remaining.ts       # Debug endpoint
├── lib/                           # TypeScript library code
│   ├── debate-engine.ts           # TypeScript debate logic (shared with API)
│   ├── prompt-log.ts              # Redis prompt logging
│   ├── rate-limits.ts             # Rate limiting utilities
│   └── request-ip.ts              # IP normalization helpers
├── components/                    # React components (empty)
├── shared/
│   └── messages.json              # Progress messages (CLI & UI shared)
├── data/                          # Data files and database
│   ├── experiments.db            # SQLite database for all experiments
│   ├── claims_verified_climate_48.json  # Verified: 48 climate claims
│   ├── claims_verified_health_50.json   # Verified: 50 health claims
│   ├── claims_gpt5_01.json              # GPT-5 generated claims (set 1)
│   ├── claims_gpt5_02.json              # GPT-5 generated claims (set 2)
│   ├── debate_motions.json              # 37 real debate motions with voting data
│   ├── google-fact-check/
│   │   ├── raw/                         # Unprocessed API responses
│   │   ├── cleaned/                     # Cleaned claims
│   │   └── verification-mods/           # Modification logs
│   └── debate-podcasts/
│       ├── raw/                         # CSV files from debate series
│       └── README.md                    # Debate podcast data documentation
├── plotting/                      # Visualization scripts and outputs
│   ├── scripts/                  # 27+ plotting scripts
│   └── plots/                    # Generated visualization files
├── topics.json                    # Topic list for claim categorization
├── requirements.txt               # Python dependencies
├── package.json                   # Node.js dependencies
├── docs/
│   ├── CLAUDE.md                 # This file - implementation context
│   ├── DEPLOYMENT.md             # Vercel deployment guide
│   └── FACTCHECK_SETUP.md        # Google Fact Check API setup guide
├── .env                          # Environment variables (gitignored)
├── .env.example                  # Environment variable template
└── README.md                     # Project vision and roadmap
```

### Test Data

The project includes fact-checked claims from Google's Fact Check Tools API for testing:

All claims data is now organized in the `data/` directory:

**Ready-to-use claims (in `data/`):**
- **claims_verified_climate_48.json** - 48 verified climate claims from fact-checkers
- **claims_verified_health_50.json** - 50 verified health claims from fact-checkers
- **claims_gpt5_01.json** - GPT-5 generated claims (set 1)
- **claims_gpt5_02.json** - GPT-5 generated claims (set 2)
- **debate_motions.json** - 37 real-world debate motions from debate podcasts (see below)

**Google Fact Check API data (in `data/google-fact-check/`):**
- `raw/` - Unprocessed API responses (e.g., claims_historical_health_50.json, claims_historical_climate_50.json, claims_recent_30days.json)
- `cleaned/` - Cleaned and standardized claims (e.g., claims_cleaned_health_50.json)
- `verification-mods/` - Verification modification logs

**Debate Podcast data (in `data/debate-podcasts/`):**
- `raw/` - CSV files from Munk Debates, Open To Debate, and Soho Forum
- `debate_motions.json` - 37 processed debate motions with pre/post voting data and winners
- See `data/debate-podcasts/README.md` for full documentation

These verified datasets have been cleaned and enhanced by LLMs to ensure claims are:
- Specific and factually debatable
- Include necessary temporal/geographical context
- Accurately match fact-checker article content
- Have correct verdict mappings (supported/contradicted/misleading/needs more evidence)

Use these to test the debate system's accuracy by comparing verdicts with professional fact-checker ratings. See [FACTCHECK_SETUP.md](FACTCHECK_SETUP.md) for how to fetch and process more claims.

#### Debate Podcast Motions

The `debate_motions.json` file contains 37 motions from real-world debates with actual voting data:

- **Sources**: Munk Debates (18), Open To Debate (7), Soho Forum (12)
- **Topics**: Politics (26), Economics (4), Health (3), Technology (3), Religion (1)
- **Data includes**: Pre/post debate voting percentages, vote swing, winner determination

These motions differ from fact-checked claims in an important way:
- **Fact-checked claims** evaluate **truth** (verdict: supported/contradicted/misleading/needs more evidence)
- **Debate motions** evaluate **persuasiveness** (winner: who changed more minds in the actual debate)

A debate "won" by the For side doesn't necessarily mean the claim is true—it means the For side was more persuasive in that particular debate. This data can be used to:
- Compare AI debate outcomes to real human debate outcomes
- Test whether AI debates produce similar vote swings
- Benchmark persuasion strategies against real-world data

### Running Experiments

The debate system automatically saves all experiment results to a SQLite database for easy querying and analysis.

#### Debate Suites

For systematic testing, debates can be run in "suites" of 4 configurations to control for order effects:
- **2 debater orders**: Model A arguing Pro vs Model B arguing Con, and vice versa
- **2 turn orders**: Pro going first vs Con going first

This 2×2 design (4 debates total) helps isolate the effect of argument strength from confounding factors like first-mover advantage or model-specific biases toward certain argument positions.

Use `run_debate_motion_suite.py` to run all 4 configurations automatically:

```bash
python run_debate_motion_suite.py --motion 2 --debater1 claude --debater2 gpt4
```

This will run all 4 debate configurations for motion index 2 from `data/debate_motions.json`. The political correctness motion (index 2) has been run with all 6 possible debater matchups (claude-gemini, claude-gpt4, claude-grok, gemini-gpt4, gemini-grok, gpt4-grok), providing a comprehensive comparison of model debating capabilities on the same topic.

#### Individual Experiments

```bash
python debate.py "Your claim here" \
  --turns 2 \
  --topic climate \
  --claim-id "data/claims_gpt5_01.json:0" \
  --gt-verdict supported \
  --gt-source "Science Magazine"
```

Options for experiments:
- `--topic TOPIC`: Specify claim topic (climate, health, etc.)
- `--claim-id ID`: Claim ID in format "filename:index" (e.g., "data/claims_gpt5_01.json:0")
- `--gt-verdict VERDICT`: Ground truth verdict (supported/contradicted/misleading/needs more evidence)
- `--gt-source SOURCE`: Ground truth source (e.g., "gpt5", publisher name)
- `--gt-url URL`: Ground truth URL
- `--con-first`: Have con debater go first instead of pro (default: pro goes first)

All experiments are saved to `experiments.db` in the repository root.

#### Randomized Experiment Sweeps

Use `run_experiments_randomize_all.py` to launch repeated experiment suites on randomly selected claims and model line-ups:

```bash
python run_experiments_randomize_all.py --count 10 --seed 42
```

The script samples uniformly across the `data/claims_verified_*.json` and `data/claims_gpt5_*.json` files, retries a failed suite once, and then continues so that a transient model hiccup doesn't halt the batch. Individual debates also retry once when a model returns malformed JSON.

#### Querying Experiments

Use `query_experiments.py` to search and analyze your experiments:

```bash
# List all experiments
python query_experiments.py --list

# Show statistics
python query_experiments.py --stats

# Filter by topic and score
python query_experiments.py --topic climate --min-score 7

# Filter by verdict
python query_experiments.py --judge-verdict supported

# Get specific experiment by ID
python query_experiments.py --get 5

# Export results to JSON for sharing
python query_experiments.py --topic health --export health_results.json

# Combine filters
python query_experiments.py --topic climate --gt-verdict supported --judge-verdict contradicted
```

Query options:
- `--topic`: Filter by topic
- `--judge-verdict`: Filter by judge's verdict
- `--gt-verdict`: Filter by ground truth verdict
- `--min-score` / `--max-score`: Filter by judge score
- `--pro-model` / `--con-model` / `--judge-model`: Filter by models used
- `--verbose, -v`: Show detailed information
- `--export FILE`: Export results to JSON file
- `--limit N`: Limit number of results (default: 50)

#### Experiment Schema

Each experiment includes:
- **claim_data**: The claim text, optional topic, and optional claim_id (format: "filename:index")
- **ground_truth**: Expected verdict, source, and URL (if known)
- **experiment_config**: Timestamp, models used, number of turns, who went first
- **debate_transcript**: Complete record of all arguments with sources
- **judge_decision**: Verdict, score (0-10 or null), and reasoning
- **errors_or_refusals**: Any errors or model refusals during the debate

The judge provides both a categorical verdict and a numeric score:
- **Score null**: Needs more evidence (insufficient information to determine)
- **Scores 0-4**: Contradicted (0=completely contradicted, 4=weakly contradicted)
- **Score 5**: Misleading/ambiguous
- **Scores 6-10**: Supported (6=weakly supported, 10=completely supported)

See `experiment_schema_example.json` for a complete example of the data structure.

### Prompt & Debate Logging

- Every debate request and outcome is persisted in Upstash Redis under `promptlog:*` keys, including metadata (models, turns, hashed IP, user-agent), streaming progress updates, final transcripts, verdicts, and error details when runs fail. **This logging pipeline is new and has not yet been fully tested—verify it in your environment before relying on it.**
- IP addresses are hashed with `PROMPT_LOG_IP_SALT` (falls back to `IP_HASH_SALT` if unset); set a unique salt so hashes cannot be reversed.
- Storage is capped by a configurable byte budget. Defaults (tuned for the 256 MB free tier) can be overridden via:
  - `PROMPT_LOG_MAX_BYTES` — total bytes before pruning kicks in (default ≈214 MB headroom)
  - `PROMPT_LOG_ENTRY_BYTES` — expected per-entry size used to estimate how many records to trim (default 12 KB)
  - `PROMPT_LOG_TRIM_PROBABILITY` — probability (0–1) of running the prune check on writes to spread out Redis commands (default 0.1)
- Logs live in the same Upstash instance the rate limiter uses. Inspect them with the Upstash console or via `redis-cli`/REST: e.g. `ZREVRANGE promptlog:index 0 9` to list recent debates, then `GET <key>` for the JSON payload.
- A running total of stored bytes is maintained (`promptlog:total_bytes`). When the cap is hit, the oldest entries (and their size bookkeeping) are purged automatically so storage stays within the budget.
- A local helper (`scripts/analysis/inspect_prompt_logs.py`) is available for quick checks: run `python scripts/analysis/inspect_prompt_logs.py list --limit 5 --summary` to print the newest claims/metadata (add `--include-scores` for their timestamps) or `python scripts/analysis/inspect_prompt_logs.py get <key> --summary` for a single entry. Include `--include-payloads` if you want the full debate transcript. The script auto-loads `.env` in the repo root before reaching for `UPSTASH_REDIS_REST_URL`/`TOKEN`. Like the logging pipeline, this script is new and untested—confirm results against Upstash before relying on it.

### Core Components

#### Python CLI (scripts/core/debate.py)

**1. Debater Class** (scripts/core/debate.py:20-190)
- Takes a position ("pro" or "con")
- Generates arguments with citations (URL, quote, context, argument)
- Can explicitly refuse using structured JSON format
- System prompt emphasizes participation while allowing refusal as last resort

**2. Judge Class** (scripts/core/debate.py:193-234)
- Reviews full debate transcript (including refusals)
- Assigns one of 4 verdicts: supported/contradicted/misleading/needs more evidence
- Provides brief explanation
- Retries once when JSON parsing fails before surfacing an error

**3. Debate Orchestrator** (run_debate function, scripts/core/debate.py:231-316)
- Alternates between Pro and Con for T turns
- Filters refusals from debate history shown to opponents
- Shortens debate after first refusal (allows one counter-argument)
- Passes complete transcript to judge

#### Experiment Automation

- `scripts/runners/run_experiments.py` runs the fixed 2×8 design (turn counts × debater order) for a specified claim and persists results to SQLite at `data/experiments.db`.
- `scripts/runners/run_experiments_randomize_all.py` samples random claims from the verified and GPT-5 datasets and unique model combinations. Each suite retries once on failure and the script continues to the next selection so a malformed response or transient API error does not abort the batch.

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
  - Checks: `if (used >= userLimit)` where userLimit resolves to NON_ADMIN_RATE_LIMIT or ADMIN_RATE_LIMIT
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

**Implementation** (scripts/data_processing/fetch_claims.py):
- Uses Google Fact Check Tools API with API key authentication
- **No service account needed** (API key only for `claims:search` endpoint)
- Fetches claims with customizable parameters: query, date range, language
- Saves structured JSON with claim text, claimant, fact-checker ratings, and source URLs

**Authentication Discovery**:
- Initially tried service account approach (doesn't work for read-only endpoint)
- Service accounts are only for `pages.*` write endpoints (creating ClaimReview pages)
- The `claims:search` endpoint requires API key authentication
- Can reuse existing `GOOGLE_API_KEY` (same key used for Gemini)

**API Parameters** (scripts/data_processing/fetch_claims.py:12-61):
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
2. Run debates on each claim using `scripts/core/debate.py`
3. Map fact-checker ratings to debate verdicts:
   - "False" → should get "contradicted" or "misleading"
   - "True" → should get "supported"
   - "Misleading/Needs Context" → should get "misleading" or "needs more evidence"
4. Analyze agreement rates and identify patterns/biases

**Key Learning**: Service account confusion wasted significant time. The API documentation is unclear about authentication methods. API key is simpler and correct for read-only access.

**See**: docs/FACTCHECK_SETUP.md for complete setup guide and troubleshooting.

### Data Processing Pipeline

**Purpose**: Clean and verify raw claims from the API to ensure they're suitable for debate testing.

**Problem**: Raw claims from Google Fact Check API have issues:
- Vague claim text ("Scientists have had to pause...")
- Missing temporal/geographical context
- Diverse fact-checker ratings that don't map to our 4 verdicts
- Placeholder text ("CLAIM") with no actual claim
- Some claims don't match article content

**Solution**: Two-step LLM-powered processing pipeline

**Step 1: Process Claims** (scripts/data_processing/process_factcheck_claims.py)

Cleans and standardizes raw fact-check claims using an LLM:

```bash
python scripts/data_processing/process_factcheck_claims.py claims_historical_health_50.json -o test_clean_health.json --model gpt4
```

**What it does**:
- Rewrites vague claims to be standalone and debatable
- Adds temporal/geographical context (e.g., "in January 2025", "in Los Angeles")
- Maps fact-checker ratings to 4 debate verdicts (supported/contradicted/misleading/needs more evidence)
- Assigns broad topic tags from existing list (or creates new ones)
- Filters out unsuitable claims (viral videos, placeholders, non-English)

**Example transformation**:
- **Before**: "Scientists have had to pause the Climate Change Hoax Scam"
- **After**: "Climate deniers misinterpreted a 2025 Antarctic ice study to falsely claim scientists paused climate change research"

**Implementation** (scripts/data_processing/process_factcheck_claims.py):
- `get_system_prompt()`: Comprehensive prompt with verdict mapping rules, topic guidelines, and examples
- `process_single_claim()`: Calls LLM with claim + review data, parses JSON response
- Model selection: claude/gpt4/gemini/grok (default: claude)
- Resume capability: Saves after each claim, safe to interrupt
- Outputs: processed claims JSON + skipped claims log + updated topics.json

**Step 2: Verify Claims** (scripts/validation/verify_claims.py)

Second-pass quality control with URL fetching:

```bash
python scripts/validation/verify_claims.py test_clean_health.json -o test_verified_health.json --model gpt4
```

**What it does**:
- **Fetches and reads actual webpage URLs** from fact-checker articles
- Verifies claims accurately match article content
- Can modify claim/verdict/topic based on article
- Can delete claims that don't match article content
- Transparently logs all modifications before making changes

**URL Fetching Implementation** (scripts/validation/verify_claims.py:25-74):
- Uses `requests` library with proper headers and timeouts
- Parses HTML with BeautifulSoup4 to extract clean text
- Removes script/style/nav elements for cleaner content
- Limits to first ~3000 characters to stay within LLM context
- Handles errors gracefully (403 blocks, timeouts, parse failures)

**Why URL fetching is critical**:
- Ensures claims accurately represent what fact-checkers actually said
- Catches mismatches between claim and article content
- Provides LLM with actual evidence to verify verdict correctness
- Will be needed later for verifying debaters' cited sources

**Modification Logging** (scripts/validation/verify_claims.py:326-367):
- Saves complete original claim before any modifications
- Records timestamp, modified fields, and reason
- Outputs to `{output_file}_modifications.json`
- Enables audit trail and quality analysis

**Current Verified Datasets**:

1. **test_verified_climate.json** (48 claims)
   - Input: 50 raw → Output: 48 verified (1 deleted, 32 modified)
   - Processed: October 2025 with GPT-4
   - Key fix: "Scientists paused..." → detailed explanation of Antarctic study misinterpretation

2. **test_verified_health.json** (50 claims)
   - Input: 50 raw → Output: 50 verified (0 deleted, 32 modified)
   - Processed: October 2025 with GPT-4
   - Enhanced specificity and context across many claims

**Processing Statistics**:
- ~65% modification rate (32/50 claims needed improvements)
- 1/99 claims deleted (didn't match URL content)
- Common improvements: added dates, locations, clarified vague language
- Verdict corrections: Several "misleading" → "contradicted" based on articles

**Dependencies**:
```python
requests>=2.31.0      # HTTP requests
beautifulsoup4>=4.12.0  # HTML parsing
```

**Key Design Decision**: Two-stage approach
- Stage 1: Fast processing based on claim + review metadata
- Stage 2: Thorough verification with actual article content
- Separation allows flexibility (can re-run stage 2 without re-processing)

**See**: docs/FACTCHECK_SETUP.md for complete processing pipeline guide

### Debate Podcast Data Integration

**Purpose**: Integrate real-world debate data from professional debate series to compare AI debate outcomes with human persuasiveness.

**Problem**: Need empirical data on how real debates perform—which side wins, how much minds change, what topics generate biggest swings.

**Solution**: Process CSV data from three major debate series into standardized JSON format.

**Data Sources**:

1. **Munk Debates** (18 motions)
   - High-profile debates on major global issues
   - Features prominent public intellectuals
   - Topics: politics, economics, international relations

2. **Open To Debate** (7 motions with voting data)
   - Policy-focused debates on current issues
   - Audience voting before/after debate
   - Topics: technology, economics, politics

3. **Soho Forum** (12 motions)
   - Libertarian-oriented Oxford-style debates
   - Clear winner determination by vote swing
   - Topics: politics, economics, health policy

**Processing Implementation** (scripts/data_processing/process_debate_podcasts.py):

```bash
python scripts/data_processing/process_debate_podcasts.py data/debate-podcasts/raw/ -o data/debate_motions.json --model claude
```

**What it does**:
- Parses three CSV files with different formats
- Normalizes voting percentages and date formats
- Assigns topics using LLM (same topic list as fact-checked claims)
- Outputs unified JSON with 37 debate motions

**Data Structure**:
```json
{
  "motion": "The standalone debatable claim/resolution",
  "date": "ISO 8601 timestamp or null",
  "source": "Munk Debates|Open To Debate|Soho Forum",
  "sourceUrl": null,
  "preVote": {"for": 50.0, "against": 50.0},
  "postVote": {"for": 34.0, "against": 66.0},
  "voteSwing": {"pro": -16.0},
  "winner": "For|Against|Draw",
  "type": "debate_motion",
  "topic": "politics|economics|health|technology|religion"
}
```

**Key Distinction from Fact-Checked Claims**:
- **Fact-checked claims**: Evaluate truth (verdict: supported/contradicted/misleading/needs more evidence)
- **Debate motions**: Evaluate persuasiveness (winner: who changed more minds)

A debate "won" by the For side doesn't mean the claim is true—it means the For side was more persuasive in that particular debate.

**Use Cases**:
1. **Benchmark AI debates** against real human debate outcomes
2. **Compare vote swings**: Do AI debates produce similar persuasion patterns?
3. **Test persuasion strategies**: Which arguments work in real debates vs AI debates?
4. **Validate judge verdicts**: Do AI judges agree with human audience voting trends?

**Topic Distribution** (as of October 2025):
- Politics: 26 motions (70%)
- Economics: 4 motions (11%)
- Health: 3 motions (8%)
- Technology: 3 motions (8%)
- Religion: 1 motion (3%)

**Data Organization**:
```
data/debate-podcasts/
├── raw/
│   ├── Munk-Debates.csv
│   ├── Open-To-Debate.csv
│   └── Soho-Forum-Debates.csv
├── README.md                      # Full documentation
└── ../debate_motions.json         # Processed output (in data/)
```

**Quality Notes**:
- Some motions have incomplete voting data (marked with null values)
- Dates normalized to ISO 8601 (some only have year precision)
- Vote swings can be positive (For gained) or negative (Against gained)
- "Draw" outcomes are rare but possible (zero vote swing)

**Integration with Experiments**:
- Debate motions can be used as claims for AI debate experiments
- Both fact-checked claims and debate motions share the `topic` field
- Allows sampling from either dataset or combination
- Compare AI verdicts with human voting outcomes

**See**: data/debate-podcasts/README.md for complete documentation and examples

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
NON_ADMIN_RATE_LIMIT=5                # Default: 5 uses/model/day
GLOBAL_MODEL_LIMIT=200                # Default: 200 uses/model/day (global backstop)

# Notes:
# - Localhost (::1, 127.0.0.1) treated as admin when ADMIN_IP is set
# - Non-admin IPs get NON_ADMIN_RATE_LIMIT uses/model/day (defaults to 5)
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

**Problem**: We need per-IP limits (5/day) plus an admin override (500/day) while presenting accurate remaining counts in the UI and protecting against distributed abuse.

**Solution** (pages/api/debate.ts, pages/api/check-rate-limit.ts, lib/request-ip.ts):
- Normalize client IPs (handles `x-forwarded-for`, IPv6, ports) so Redis buckets are consistent locally and on Vercel
- Use a single Upstash sliding-window limiter configured with the admin ceiling (ADMIN_RATE_LIMIT) and derive per-user usage (`used = ADMIN_RATE_LIMIT - remaining`)
- Persist per-IP usage snapshots to Redis (`ratelimit:usage:<ip>:<model>`) so the web UI can read true remaining counts across refreshes and restarts
- Add a global backstop limiter (default 200 free-tier calls per model per 24h, configurable via `GLOBAL_MODEL_LIMIT`) that shares usage across all IPs (`ratelimit:usage-global:<model>`)
- Surface both per-user and global remaining counts via `/api/check-rate-limit`
- Disable models client-side when either quota hits zero and guide users to add their own API keys

**Benefits**:
- Accurate, persistent usage reporting in the web UI
- Shared global guardrail to deter distributed abuse
- Same logic powers both CLI and UI via shared storage keys

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

**Solution** (lib/request-ip.ts, pages/api/debate.ts):
```typescript
const identifier = getClientIp(req); // normalizes x-forwarded-for, strips ports
const isLocalhost = isLocalhostIp(identifier);
const isAdmin = Boolean(ADMIN_IP && (identifier === ADMIN_IP || isLocalhost));
```

**Result**: Admin privileges hinge on `ADMIN_IP`, while localhost still resolves to the admin allowance in development.

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

### Important Note: GPT-4 Model Change (November 2025)

**Post-Experiment Model Update**: After completing all experiments documented in README.md, the GPT-4 model ID was updated from `gpt-4-turbo-preview` to `gpt-4o` on November 6, 2025 to fix user API key compatibility issues.

**Why this matters for reproducibility**:
- All experiments in the writeup used `gpt-4-turbo-preview`
- The model change may affect future results, though both are GPT-4-class models
- Experiments are not literally reproducible anyway (temperature > 0 for all API calls)
- This note ensures transparency about the model configuration timeline

**User impact**:
- Users with new/free-tier OpenAI API keys were getting 404 errors with `gpt-4-turbo-preview`
- Server API keys retained access to the deprecated model, causing inconsistent behavior
- Update to `gpt-4o` ensures compatibility with all API key types
- `gpt-4o` is OpenAI's current recommended GPT-4 model as of November 2025

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

- **Rate limit helper**: `python scripts/utils/check_rate_limits.py [ip]` shows cached usage, sliding-window entry counts, and global backstop usage for each model (defaults to `127.0.0.1`). Install `python-dotenv` if you want the script to auto-load `.env`.
- **Reset helper**: `python scripts/utils/check_rate_limits.py [ip] --reset [--include-global]` clears the per-IP cache, the Upstash sliding window entries, and (optionally) the global backstop so you can start a fresh test run.

**Test different IPs**:
- Localhost: Should get ADMIN_RATE_LIMIT (default 500)
- Other IPs: Should get NON_ADMIN_RATE_LIMIT (default 5)
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

### Plotting Scripts

Several plotting scripts are available to visualize debate results:

#### Debate Motion Plots (4-subplot format)

**Full debate suites** (same motion with 4 configurations):
- `plotting/scripts/create_debate_plot.py` - Creates a 4-subplot plot for debates matching a motion pattern
- `plotting/scripts/generate_all_debate_plots.py` - Generates all 8 standard debate motion plots
- Output: `plotting/plots/debate-motions/`
- Each plot shows 4 subplots: (pro-first vs con-first) × (debaters swapped)
- Shows judgment trajectories across all debate turns for all 4 judges

**Duplicate judgment analysis**:
- `plotting/scripts/create_debate_plot_max.py` - Same as above but uses MAX(id) for deduplication
- `plotting/scripts/generate_all_debate_plots_max.py` - Generates all 8 plots with MAX deduplication
- Output: `plotting/plots/debate-motions-with-duplicate-judging/`
- Used to analyze how judgments changed when debates were re-judged

#### Turn Progression Plots (legacy schema experiments)

Early experiments used a different schema where debates were run with varying turn counts (1, 2, 4, 6 turns) but judged only at the end. These plots show how judge scores evolve as debate length increases:

**Paired experiments** (same debaters switching sides):
- `plotting/scripts/create_turn_progression_pair_plot.py` - Creates side-by-side plots for paired experiments
- `plotting/scripts/generate_all_turn_progression_pairs.py` - Generates all 16 paired plots
- Output: `plotting/plots/score-by-turn-pairs/`
- Filename format: `{shortname}_debaters-{model1}-{model2}_judge-{judge}.png`
- Left subplot: alphabetically earlier debater as Pro
- Right subplot: alphabetically earlier debater as Con
- Shows how the same judge's score changes with debate length for both debater orientations

**Single experiments** (no matching pair):
- `plotting/scripts/create_turn_progression_plot.py` - Creates single plot for one experiment
- Output: `plotting/plots/score-by-turn/`
- Filename format: `{shortname}_pro-{pro}_con-{con}_judge-{judge}.png`
- Shows judge score progression across turns 1, 2, 4, 6

**Claim shortnames**:
- `plotting/scripts/claim_shortnames.py` - Maps full claim texts to short descriptive names used in filenames
- Examples: "homeopathy-studies", "minimum-wage", "climate-models-overestimate"

**Helper scripts**:
- `plotting/scripts/cleanup_and_rename_misc_debates.py` - Consolidates paired experiments and renames singles

#### Judge Analysis Plots

**Self-scoring patterns**:
- `plotting/scripts/create_self_score_plot.py` - Shows how judges score when judging debates they participated in
- `plotting/scripts/generate_all_self_score_plots.py` and `generate_all_self_score_plots_full_debate.py`
- Output: `plotting/plots/self-score-histogram/`
- 3 vertical subplots per judge: all scores, scores when judging self as Pro, scores when judging self as Con
- Supports normalized density plots (via `normalized=True` parameter) for direct comparison across different sample sizes
- Key finding: Claude/GPT-4 heavily use score 5 (~50-60%), Gemini is more decisive

**Judge-debater agreement (histograms)**:
- `plotting/scripts/create_judge_debater_agreement_plot.py` - Shows score distributions for one judge scoring one debater
- `plotting/scripts/generate_all_judge_debater_agreement_plots.py`
- Output: `plotting/plots/judge-debater-agreement-histogram/`
- 2 vertical subplots: debater as Pro, debater as Con
- Filename: `judge={judge}_debater={debater}_agreement.png` (or `*_normalized.png` for density plots)
- Supports normalized density plots for direct comparison
- Key finding: Gemini trusts Claude, distrusts GPT-4

**Judge-debater agreement (violin plots)**:
- `plotting/scripts/create_judge_debater_agreement_violin.py` - Comprehensive 4×5 violin plot grid
- `plotting/scripts/generate_judge_debater_agreement_violin.py`
- Output: `plotting/plots/judge-debater-agreement-violin/`
- Grid layout: 4 rows (judges) × 5 columns (overall + 4 debaters)
- Column 1: Overall score distribution for each judge (colored by judge's model color)
- Columns 2-5: Split violin plots showing Con (left, red) vs Pro (right, green) distributions
- All violins normalized to equal visual area (representing densities, not counts)
- Shows both mean (white diamond) and median (black circle) markers
- When mean and median are close (<0.3 score units), markers are horizontally offset for visibility
- Enables direct comparison of scoring patterns across all judge-debater-side combinations

**Judge-judge agreement**:
- `plotting/scripts/create_judge_judge_agreement_plot.py` - Scatterplots comparing two judges' scores
- `plotting/scripts/generate_all_judge_judge_agreement_plots.py` and `generate_all_judge_judge_agreement_plots_full_debate.py`
- Output: `plotting/plots/judge-judge-agreement-scatterplot/`
- Shows correlation between judge pairs with jitter to reduce overplotting
- Filename: `{judge1}-{judge2}-judge-judge-agreement.png` (or `*-full_debate_only.png`)
- Correlations range from 0.67 (Gemini-GPT4) to 0.87 (Gemini-Grok) for full debates

#### Debate Visualization Details

**create_debate_plot.py** - Production plotting script
- Generates 2×2 subplot grids for the full Claude vs Grok debate suite
- Each subplot shows one of four experimental conditions:
  - Top-left: Claude Pro → Grok Con (Pro, then Con)
  - Top-right: Grok Con → Claude Pro (Con, then Pro)
  - Bottom-left: Grok Pro → Claude Con (Pro, then Con)
  - Bottom-right: Claude Con → Grok Pro (Con, then Pro)

**generate_all_debate_plots.py** - Batch generation script
- Generates plots for all three main debate motions
- Outputs: `political_correctness_debates.png`, `anti_zionism_debates.png`, `cold_war_debates.png`

### Plot Features

**Visual Design:**
- **Color scheme**:
  - Judge models: Claude (purple), Gemini (blue), GPT-4 (orange), Grok (bright pink)
  - Pro/Con labels: Green (#007000) for "Supported", Red (#D22222) for "Contradicted"
- **Model hierarchy**: When scores collide at a turn, models are offset vertically by fixed order:
  1. Claude (highest/top)
  2. Gemini
  3. GPT-4
  4. Grok (lowest/bottom)
- **Open circles**: "Needs more evidence" rulings (not scored, plotted at y=5)
- **Dashed lines**: Connect rulings that include "needs more evidence"
- **Solid lines**: Connect all other rulings
- **Small font note**: Bottom of figure explains open circles and dashed lines

**Layout:**
- **Main title**: Centered at top with ample spacing above/below
- **Column labels**: "Pro, then Con" and "Con, then Pro" positioned above subplot columns
- **Row labels**: "Pro = Claude, Con = Grok" and "Pro = Grok, Con = Claude" rotated 90° on left side
- **Subplot titles**: Colored text showing debater models and positions (e.g., "Claude arguing Pro, then Grok arguing Con")
- **Axes**: X-axis shows debate turns (1-6), Y-axis shows score (0-10)
- **Reference labels**: "Supported" (green) near y=9, "Contradicted" (red) near y=1

### Key Implementation Details

**Dynamic Offset Calculation** (`calculate_offsets()` function):
```python
def calculate_offsets(judge_data):
    """
    Calculate offsets for each model based on score collisions.
    Returns a dict mapping (judge_model, turn) -> offset
    """
```
- Detects which judge models have colliding scores at each turn
- Assigns vertical offsets based on MODEL_ORDER hierarchy
- Offsets are context-dependent (only applied when scores actually collide)
- Two models colliding: ±0.1 offset
- Three models colliding: -0.15, 0, +0.15
- Four models colliding: -0.15, -0.05, +0.05, +0.15

**Color Constants:**
```python
MODEL_COLORS = {
    'claude-sonnet-4-5-20250929': '#8B5CF6',  # purple
    'gemini-2.5-flash': '#2424bf',  # blue
    'gpt-4-turbo-preview': '#F97316',  # lighter orange
    'grok-3': '#f96bf3'  # bright pink
}

PRO_COLOR = '#007000'  # green
CON_COLOR = '#D22222'  # red
```

**Spacing Parameters:**
```python
fig.subplots_adjust(
    hspace=0.40,    # vertical space between subplot rows
    wspace=0.35,    # horizontal space between subplot columns
    top=0.76,       # top margin (makes room for column labels)
    bottom=0.10,    # bottom margin (makes room for note)
    left=0.14,      # left margin (makes room for row labels)
    right=0.97      # right margin
)
```

### Usage

**Generate single plot:**
```bash
python create_debate_plot.py
# Outputs: political_correctness_debates.png
```

**Generate all plots:**
```bash
python generate_all_debate_plots.py
# Outputs: political_correctness_debates.png, anti_zionism_debates.png, cold_war_debates.png
```

**Customize for different motion:**
```python
create_debate_plot('%your search pattern%', 'output_filename.png')
```

### Generated Plots

**Current debate motions with full visualization:**

1. **political_correctness_debates.png**
   - Motion: "As of 2018, what critics called political correctness represented genuine progress."
   - Pattern: `%political correctness%`

2. **anti_zionism_debates.png**
   - Motion: "As of 2024, anti-Zionism is anti-Semitism."
   - Pattern: `%anti-Zionism is anti-Semitism%`

3. **cold_war_debates.png**
   - Motion: "As of 2025, the United States started the new Cold War with Russia and provoked Russia's invasion of Ukraine."
   - Pattern: `%United States started the new Cold War%`

All three represent the complete 4-experiment suite (2 debater assignments × 2 turn orders) judged by all four models (Claude, Gemini, GPT-4, Grok) across 6 turns each.

### Design Iterations

The plotting system went through several iterations to achieve publication quality:

**Legacy iteration (retired):**
- Fixed model offsets (hardcoded per model)
- Basic spacing and layout
- Original green/red colors

**Current iteration (`create_debate_plot.py`):**
- Dynamic offset calculation (only when scores collide)
- Model hierarchy ordering (Claude > Gemini > GPT-4 > Grok)
- Improved spacing (column/row labels don't overlap)
- Updated color scheme (darker green #007000, red #D22222)
- Commas in column labels ("Pro, then Con")
- Bottom note explaining open circles and dashed lines
- Smaller open circle markers matching filled marker size

### Future Enhancements

**Potential additions:**
- Statistical significance markers (e.g., asterisks for p<0.05)
- Confidence intervals around judge scores
- Win/loss annotations per subplot
- Vote swing comparisons (for debate motions with voting data)
- Cross-motion comparison panels
- Interactive HTML versions with hover tooltips

## Experimental Results

### Initial Findings (October 2025)

**Experiment Setup**:
- Database: SQLite with full experiment tracking (experiments.db)
- Judge: GPT-4 for all experiments
- Debaters: Claude Sonnet 4.5 and Grok 3
- Two claims tested with 8 experiments each (T=1,2,4,6 × 2 debater orderings)

**Experiment 1: Homeopathic Remedies Claim**
- **Claim**: "Homeopathic remedies are scientifically proven to work better than placebos"
- **Ground Truth**: contradicted
- **Claim ID**: claims_gpt5_01.json:1
- **Results**: 7/8 correct (87.5% accuracy)
  - Claude pro/Grok con: needs evidence → misleading → misleading → **contradicted**
  - Grok pro/Claude con: misleading → contradicted → contradicted → contradicted
- **Key Finding**: Clear convergence toward ground truth as turns increase
- **Note**: At T=4 with Claude pro, Claude refused to argue the pro side, citing lack of credible evidence

**Experiment 2: Minimum Wage Claim**
- **Claim**: "After controlling for inflation and productivity growth, raising the federal minimum wage modestly does not consistently cause overall job losses"
- **Ground Truth**: supported
- **Claim ID**: claims_gpt5_01.json:5
- **Results**: 1/8 correct (12.5% accuracy)
  - Claude pro/Grok con: needs evidence → misleading → misleading → **supported** ✓
  - Grok pro/Claude con: misleading → contradicted → contradicted → contradicted
- **Key Finding**: Strong debater effect - Claude arguing con consistently won even though ground truth supports the claim

**Cross-Experiment Insights**:

1. **Controversy Matters**: The homeopathic claim (pseudoscience) showed 87.5% accuracy with clear convergence. The minimum wage claim (genuine economic controversy) showed only 12.5% accuracy with no convergence pattern.

2. **Debater Strength Effects**: When Claude argued con on the minimum wage claim, it consistently won across all turn counts (T=1,2,4,6), suggesting the debate system can be dominated by debater skill rather than ground truth for genuinely controversial claims.

3. **Turn Count Effects**:
   - Simple claims: More turns → convergence to truth (homeopathic remedies)
   - Controversial claims: More turns → no consistent convergence (minimum wage)
   - The core hypothesis (longer debates favor truth) holds for clear-cut cases but not for legitimately contested topics

4. **First-Mover Effects**: Limited evidence so far, but worth investigating further with more experiments.

5. **Model Behavior**:
   - Claude refused to argue pro-homeopathy at T=4 (ethical refusal)
   - Both models found credible-sounding evidence for both sides of minimum wage debate
   - Judge (GPT-4) struggled with claims where both sides had legitimate evidence

**Implications for Research**:
- Need to test more claims across the controversy spectrum
- Should track which side each model prefers (potential model-specific biases)
- The debate system works well for debunking pseudoscience but struggles with genuine academic/policy disagreements
- Ground truth labels may be insufficient for truly controversial claims (expert consensus might disagree with label)

**Next Steps**:
- Run experiments on more claims from verified datasets (climate, health)
- Analyze model-specific win rates and refusal patterns
- Test whether certain topics systematically favor one side
- Compare judge verdicts with multiple fact-checker ratings

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

### 7. Sample Debate Cards (November 2025)

**Purpose**: Allow users to quickly start a debate without thinking of a claim.

**Problem**: Users face blank textarea on first visit. Providing examples reduces friction and showcases the app's capabilities.

**Solution**: Responsive grid of 6 sample debate cards with smart model selection.

**Implementation** (lib/sample-debates.ts, pages/index.tsx):

**Key Design Decisions**:

1. **Pre-computation over Random Retry**
   - Generates all 128 possible debate configs (4 models³ × 2 turn counts)
   - Filters to valid configs based on available free uses
   - Samples 6 configs with replacement from valid pool
   - **Performance**: 0.3-0.6ms (100x faster than previous retry-based approach)

2. **Sampling with Replacement**
   - User might see duplicate model combinations (e.g., Claude vs Claude)
   - Always shows exactly 6 cards if ANY valid config exists
   - Simplifies logic: no need for "disabled" card states

3. **Adaptive Reconfiguration**
   - Cards silently reconfigure after each debate
   - Example: Card previously had 2 turns → now only 1 turn possible → adjusts automatically
   - Example: Card previously used Claude → now Claude exhausted → picks different model
   - User doesn't notice unless paying close attention

4. **Responsive Design**
   - Desktop (>900px): 3 columns × 2 rows = 6 cards
   - Tablet (600-900px): 2 columns × 3 rows = 6 cards
   - Mobile (<600px): 1 column × 2 rows = 2 cards (CSS display:none hides others)

5. **Card Content**
   - Claim text (14px bold)
   - Debater models (12px): "Pro: Claude • Con: GPT-4"
   - Judge model (12px): "Judge: Gemini"
   - Turn count + opening side (11px): "2 turns • Pro argues first"
   - "Run this debate!" button

6. **UI States**
   - Cards gray out during debates (opacity: 0.5, no pointer events)
   - No disabled states (if no valid configs, section doesn't render)
   - "Or, create your own!" heading only shows when cards present

**Sample Claims** (hardcoded in lib/sample-debates.ts):
1. "A hot dog is a sandwich."
2. "Pineapple belongs on pizza."
3. "Cats make better pets than dogs."
4. "Remote work is superior to office work."
5. "Social media does more harm than good."
6. "The Oxford comma is necessary."

**Cost Calculation**:
- 1-turn debate: (1 × 2) + 1 = 3 total API calls
- 2-turn debate: (2 × 2) + 1 = 5 total API calls
- Pro model: `turns` uses
- Con model: `turns` uses
- Judge model: 1 use (always)

**Files Modified**:
- `lib/sample-debates.ts` - New file with generation logic
- `pages/index.tsx` - Added cards section, state management, click handler
- Toggle labels: "Pro starts" / "Con starts" → "Pro" / "Con"

**Performance Optimization**: Pre-computation approach avoids nested retry loops, enabling sub-millisecond card generation even with complex validation logic.

### 8. Redis Pipelining Optimization (November 2025)

**Problem**: Rate limit check on page load was taking **~11.6 seconds** on airplane WiFi (~2 Mbps upload, high latency).

**Root Cause**:
- For each of 4 models: 4 sequential Redis calls (get, zcard, zcard, get)
- Total: 4 models × 4 calls = **16 sequential round-trips** to Upstash
- On high-latency connections: 16 × ~700ms = 11.2 seconds

**Solution**: Batch all Redis commands using pipeline

**Implementation** (pages/api/check-rate-limit.ts):

```typescript
// Before: 16 sequential awaits
for (const modelKey of modelKeys) {
  const usedRaw = await redis.get(usageKey);      // call 1
  const result = await redis.zcard(slidingKey);    // call 2
  const globalResult = await redis.zcard(globalSlidingKey); // call 3
  const globalRaw = await redis.get(globalUsageKey); // call 4
}

// After: 1 batched pipeline
const pipeline = redis.pipeline();
for (const modelKey of modelKeys) {
  pipeline.get(usageKey);
  pipeline.zcard(slidingKey);
  pipeline.zcard(globalSlidingKey);
  pipeline.get(globalUsageKey);
}
const results = await pipeline.exec(); // Single round-trip
```

**Performance Improvement**:
- **Before**: 11,586ms (16 round-trips)
- **After**: 1,255ms (1 round-trip)
- **Speedup**: **9.2x faster** on airplane WiFi
- **Expected on normal WiFi**: Probably 100-300ms (still faster due to reduced HTTP overhead)

**Key Benefits**:
- Dramatically faster on high-latency connections (airplane, mobile, international)
- Still faster on good connections (reduces HTTP overhead)
- Maintains same validation logic and error handling
- Graceful fallback if pipeline fails

**Debug Logging**:
- Server-side logs show pipeline execution time
- Client-side logs show fetch completion time
- Both kept in codebase for future performance monitoring

**Files Modified**:
- `pages/api/check-rate-limit.ts` - Replaced sequential calls with pipeline
- `pages/index.tsx` - Added timing instrumentation (kept for debugging)
- `lib/sample-debates.ts` - Added timing logs (kept for debugging)

**Upstash Pipeline Support**:
- Uses `@upstash/redis` v1.28.0 built-in pipeline support
- Pipeline queues commands, executes in single HTTP request
- Returns array of results in same order as commands

**Future Optimization Opportunities**:
- Could also pipeline the debate API's rate limit checks
- Consider caching rate limits client-side for 30-60 seconds

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
