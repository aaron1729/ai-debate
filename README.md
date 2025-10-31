# ai-debate

## TO-DO

run debates on the debate podcast motions! do them with or without a judge, but in any case do a bunch of after-the-fact judging per-round. probably just run the debates for 6 rounds, rather than 1,2,4,6.

## possible experiments

- different models from the same provider (e.g. gpt-4 vs. gpt-5)

- different judges of the same debates [already done some of this]

- have the two debaters switch sides and see how it goes [this is already happening in `run_experiments.py`]

- same matchup with same debaters, but in reverse order: CON argues before PRO.

- label claims by how controversial they are, and by their political polarity (if any).

## possible ways of slicing the data

- trajectory of judgments through debate turns, plotted for each judge separately.

## things to note in writeup

- data sources

- functionality


====================================



Adversarial truth-seeking through structured AI debates.

## Documentation

Full documentation is available in the `docs/` folder:
- **[CLAUDE.md](docs/CLAUDE.md)** - Implementation details and design decisions
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Vercel deployment guide
- **[FACTCHECK_SETUP.md](docs/FACTCHECK_SETUP.md)** - Google Fact Check API setup for test data

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

3. Run a debate:
```bash
python debate.py "Your claim here" --turns 2
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

Use these to test the debate system's accuracy by comparing verdicts with professional fact-checker ratings. See [FACTCHECK_SETUP.md](docs/FACTCHECK_SETUP.md) for how to fetch and process more claims.

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

##### Processing and Cleaning Debate Motions

**1. Process raw CSV data from debate podcasts:**
```bash
python process_debate_podcasts.py data/debate-podcasts/raw/ -o data/debate-podcasts/debate_motions_collated.json --model claude
```

**2. Clean motions to be standalone and unambiguous:**
```bash
python clean_debate_motions.py data/debate-podcasts/debate_motions_collated.json --model claude
```

The cleaning script (`clean_debate_motions.py`) uses an LLM to rewrite debate motions with:
- **Temporal context**: All motions include year/date references (e.g., "As of 2019", "In 2016", "In the context of 2013")
- **Correct verb tenses**: Past tense for historical events, past conditional for then-future possibilities
- **Clarified references**: Ambiguous terms like "we" are replaced with specific entities (e.g., "the United States")
- **Complete sentences**: All motions end with proper punctuation
- **Statement format**: Questions converted to statements (e.g., "Is war inevitable?" → "War is inevitable.")

The cleaning process:
- Takes `data/debate-podcasts/debate_motions_collated.json` (raw motions from CSV processing)
- Outputs `data/debate_motions.json` (cleaned motions for debates)
- Logs all changes to `data/debate-podcasts/debate_motions.modifications.json` for transparency
- Includes retry logic for API errors (up to 2 attempts per motion)

Output files:
- `data/debate_motions.json` - Final cleaned motions ready for use
- `data/debate-podcasts/debate_motions_collated.json` - Original collated motions (preserved for reference)
- `data/debate-podcasts/debate_motions.modifications.json` - Detailed log of all changes made

##### Temporal Constraints in Debates

When debate motions include temporal context (e.g., "As of 2019", "In 2016"), the debate system automatically enforces temporal constraints:

**For Debaters:**
- Can ONLY reference facts, events, and evidence from the specified year or earlier
- References to information after the specified year are flagged as invalid
- Helps ensure historically accurate debates that reflect the knowledge available at that time

**For Judges:**
- Instructed to IGNORE any references to events after the specified year
- Only consider evidence and arguments from the specified year or earlier
- Ensures fair evaluation based on information available at the time of the original debate

This feature is automatically applied to any claim/motion that begins with temporal framing patterns:
- "As of [YEAR]" (e.g., "As of 2019, the capitalist system was broken...")
- "In [YEAR]" (e.g., "In 2016, Donald Trump could make America great again...")
- "In the context of [YEAR]" (e.g., "In the context of 2013, men were obsolete...")

Non-temporal motions are unaffected by these constraints.

### Running Experiments

The debate system automatically saves all experiment results to a SQLite database for easy querying and analysis:

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

### Randomized Experiment Sweeps

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

## outline

tagline: "real-time AI-powered snopes".

a central hypothesis is that as the debate length increases, the judge's verdict will stabilize -- presumably erring towards the truthful side (which requires human-labeled inputs). said differently, misleading arguments are more likely to win in short debates.

### MVP

make a script, as follows.

it takes in a user-provided assertion which may be true/false/misleading (e.g. about current events in the news). two "debater" LLMs debate it, each instructed to argue as strongly as possible either in favor of or against the claim. the system prompt will indicate that they're in this setup, to hopefully avoid refusals to answer, along with a few small examples to illustrate.

in each turn of the debate, each debater gets to share a source URL, a short quote therefrom, and a little bit of context (say at most 50 words). they each get `T` turns in the debate, with say `T ∈ {1, 2, 4, 6}`.

afterwards, a "judge" LLM judges who won the debate, with a brief explanation. they're offered four labels to choose from: "supported", "contradicted", "misleading", and "needs more evidence".

the user can also review the debate to decide for themselves.

for the MVP, just use API calls to claude only.

### extensions

- [ ] save snapshots of the cited webpages.
- [ ] verify that the cited webpages contain the claimed evidence.
- [x] add chatGPT, grok, gemini, and maybe others.
- [ ] assess how different LLMs do, perhaps depending on the nature of the debate -- particularly the political leanings of the sides that the LLMs are instructed to defend.
- [x] integrate Google Fact Check Tools API to fetch test claims with ground truth labels.
- [ ] run systematic tests comparing debate verdicts with fact-checker ratings.
- [ ] allow the input of an entire news article, either in plain text or as a website. in this case, the first step is to extract specific claims; then, those are fed into the above pipeline.
- [ ] weight sources according to credibility, e.g. ranging from government websites and reuters down towards blog posts and news sources that are known to be politically biased.
- [ ] have multiple judges (a "mixture of experts"); average their scores, or have another judge that synthesizes their scores.
- [ ] save all the data (including metadata such as the topic of debate), and try to extract specific learnings -- about debates in general (e.g. first-mover dis/advantage), varying sources, and specific LLMs.
- [x] make this into a webpage, where a user can input their own claim or news article (and probably their own API key(s)).
- [ ] deploy webpage.
- [ ] add an RL policy that learns which actions lead to higher final scores (depending on various hyperparameters such as the costs of various citations). this can be a single policy that updates after debates against a frozen opponent, or ideally multiple policies that learn through self-play.
