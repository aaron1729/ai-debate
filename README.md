# ai-debate

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

The web version includes:
- 5 free debates per IP per 24 hours
- Option for users to provide their own API keys for unlimited usage
- Support for 4 models (Claude, GPT-4, Gemini, Grok)

### Test Data

The project includes fact-checked claims from Google's Fact Check Tools API for testing:
- **claims_recent_30days.json** - 6 recent political claims
- **claims_historical_health_50.json** - 50 health-related claims
- **claims_historical_climate_50.json** - 50 climate-related claims

Use these to test the debate system's accuracy by comparing verdicts with professional fact-checker ratings. See [FACTCHECK_SETUP.md](docs/FACTCHECK_SETUP.md) for how to fetch more claims.

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
- [ ] verify that the cited webpages contain the claimed evidence (being careful with phishing, etc.).
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