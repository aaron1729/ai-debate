# AI Debate in 2025

<p align="center">
  <a href="https://ai-debate-4-u.vercel.app/">
    <img src="public/hero/ai-debate-display-2400x1260.png" alt="AI Debate Hero" width="400" style="max-width: 100%; height: auto; border-radius: 12px;">
  </a>
</p>

# TO DO

- [ ] finish writeup
- [ ] add ToC

## Abstract

We implement [AI Safety via Debate](https://arxiv.org/abs/1805.00899) (Irving et al., 2018), a proposed mechanism for AI alignment, within the context of natural language debates between LLMs. This comprises the following steps, which are each elaborated upon in more detail below.
- We implement an end-to-end pipeline for running automated debates with two LLM debaters and an LLM judge. This is pipeline is also deployed as a web app [here](https://ai-debate-4-u.vercel.app/).
- We source, clean, and verify datasets from a variety of sources:
  - the Google Fact Check Claim Search API;
  - direct generation via LLM;
  - debates motions from popular debate podcasts.
  Specifically, we obtain debate claims from all three of these sources, and we obtain ground-truth labels from the former two sources.
- We run 280 debates in total, and analyze the results from a number of different angles.

We begin with a brief discussion of the context for this demo project, and we conclude by enumerating some open directions for further investigation.

The code itself was primarily written in collaboration with Claude Code. The repo itself is organized for further iteration, with extensive documentation (see particularly [docs/claude.md](docs/claude.md)). Please feel free to experiment and make a PR!

## Introduction and Context

The 2018 paper [AI Safety via Debate](https://arxiv.org/abs/1805.00899) proposes a mechanism for AI alignment: training agents via self-play in a zero-sum debate game. It is proposed that this may be useful in contexts where a human can adequately judge the end result despite not being able to evaluate turn-by-turn performance. (This is the case with complex games like Go or Chess, and the paper draws an extensive analogy with the distinction between P and NP algorithms.) As a proof-of-concept, this is implemented within the context of a very simple "debate" game: given a handwritten digit image from the MNIST dataset, two debater models try to convince a judge model of the true label by iterative revealing pixels turn-by-turn.

The years since 2018 have seen an explosion of progress in both the power and popularity of AI models, particularly ushered in by the "ChatGPT moment" in late 2022. In particular, LLMs are now extremely well-suited to the above mechanism. However, before it can be trusted as a beneficial tool for AI alignement, it must be stress-tested in this new and qualitatively different context. Such stress-testing is the primary purpose of our experiments.

## Pipeline





## Data



## Experiments


## Further Directions






## TO-DO

plot all 6-turn debates individually (not just those that came as a suite of 4, which were all from `debate_motions.json`).



## CLEANUP

everything of course, but particularly e.g.:
- data-processing scripts;
- images, and scripts for generating those;
- ...


## possible experiments

- different models from the same provider (e.g. gpt-4 vs. gpt-5)

- have the two debaters switch sides and see how it goes [this is already happening in `run_experiments.py`]

- rerun debates with _all_ the same parameters on my side (since all of the models have their own randomness -- temperature > 0).

- same matchup with same debaters, but in reverse order: CON argues before PRO.

- label claims by how controversial they are, and by their political polarity (if any).

- see if a judge appears to have an implicit bias on a given topic -- they're giving similar scores on the same topic regardless of who's debating which side.

- do judges particularly agree with their own reasoning? e.g. there could be some implicit bias towards language of the sort that the model itself generates. split this into Pro vs Con judgments.

- check based on source (gpt5, etc.).

## possible ways of slicing the data

- trajectory of judgments through debate turns, plotted all together for all judges of the same debate.

- by topic (environment, religion, politics, ...)

## things to note in writeup

- data sources; data cleaning and verification. note that some of them are much worse, and are effectively just fact-checks (particularly from the google API).

- functionality

- web UI

- compare the "political correctness debates", which involved _all_ six matchups (4 choose 2).

## Reproducibility and Analysis

### Judgment Reproducibility

Judgments are surprisingly stable: over the 8 suites of 4 debates between the same two debaters where all judges weighed in at all turns, we have judgment correlations:
- claude: 0.87
- gemini: 0.84
- gpt-4: 0.82
- grok: 0.79
(see `plotting/plots/debate-motions/` and `plotting/plots/debate-motions-with-duplicate-judging/` for visual comparison.)

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


====================================



Adversarial truth-seeking through structured AI debates.

## Documentation

Full documentation is available in the `docs/` folder:
- **[CLAUDE.md](docs/CLAUDE.md)** - Implementation details and design decisions
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Vercel deployment guide
- **[FACTCHECK_SETUP.md](docs/FACTCHECK_SETUP.md)** - Google Fact Check API setup for test data

## Project Structure

```
ai-debate/
├── scripts/                    # Python scripts organized by purpose
│   ├── core/                   # Core debate engine and storage
│   │   ├── debate.py          # Main debate engine
│   │   └── experiment_store.py # Database abstraction
│   ├── runners/               # Experiment runners
│   │   ├── run_single_debate.py
│   │   ├── run_debate_motion_suite.py
│   │   ├── run_experiments.py
│   │   └── run_experiments_randomize_all.py
│   ├── data_processing/       # Data fetching and cleaning
│   ├── validation/            # Data validation scripts
│   ├── analysis/              # Analysis and querying tools
│   └── utils/                 # Utilities and helpers
├── web/                       # Next.js web application
│   ├── pages/                 # Next.js pages (symlinked to root)
│   ├── lib/                   # TypeScript library code
│   ├── components/            # React components
│   └── shared/                # Shared resources
├── data/                      # Data files and database
│   ├── experiments.db         # SQLite database
│   ├── debate_motions.json    # Debate topics
│   └── google-fact-check/     # Fact-check data
├── plotting/                  # Visualization scripts and outputs
│   ├── scripts/               # Plotting scripts
│   └── plots/                 # Generated plots
├── docs/                      # Documentation
└── public/                    # Static assets
```

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

### Prompt & Debate Logging

- Every debate request and outcome is persisted in Upstash Redis under `promptlog:*` keys, including metadata (models, turns, hashed IP, user-agent), streaming progress updates, final transcripts, verdicts, and error details when runs fail. **This logging pipeline is new and has not yet been fully tested—verify it in your environment before relying on it.**
- IP addresses are hashed with `PROMPT_LOG_IP_SALT` (falls back to `IP_HASH_SALT` if unset); set a unique salt so hashes cannot be reversed.
- Storage is capped by a configurable byte budget. Defaults (tuned for the 256 MB free tier) can be overridden via:
  - `PROMPT_LOG_MAX_BYTES` — total bytes before pruning kicks in (default ≈214 MB headroom)
  - `PROMPT_LOG_ENTRY_BYTES` — expected per-entry size used to estimate how many records to trim (default 12 KB)
  - `PROMPT_LOG_TRIM_PROBABILITY` — probability (0–1) of running the prune check on writes to spread out Redis commands (default 0.1)
- Logs live in the same Upstash instance the rate limiter uses. Inspect them with the Upstash console or via `redis-cli`/REST: e.g. `ZREVRANGE promptlog:index 0 9` to list recent debates, then `GET <key>` for the JSON payload.
- A running total of stored bytes is maintained (`promptlog:total_bytes`). When the cap is hit, the oldest entries (and their size bookkeeping) are purged automatically so storage stays within the budget.
- A local helper (`scripts/analysis/inspect_prompt_logs.py`) is available for quick checks: run `python scripts/analysis/inspect_prompt_logs.py list --limit 5 --summary` to print the newest claims/metadata (add `--include-scores` for their timestamps) or `python scripts/analysis/inspect_prompt_logs.py get <key> --summary` for a single entry. Include `--include-payloads` if you want the full debate transcript. The script auto-loads `.env` in the repo root before reaching for `UPSTASH_REDIS_REST_URL`/`TOKEN`. Like the logging pipeline, this script is new and untested—confirm results against Upstash before relying on it.

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
python scripts/data_processing/process_debate_podcasts.py data/debate-podcasts/raw/ -o data/debate-podcasts/debate_motions_collated.json --model claude
```

**2. Clean motions to be standalone and unambiguous:**
```bash
python scripts/data_processing/clean_debate_motions.py data/debate-podcasts/debate_motions_collated.json --model claude
```

The cleaning script (`scripts/data_processing/clean_debate_motions.py`) uses an LLM to rewrite debate motions with:
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
