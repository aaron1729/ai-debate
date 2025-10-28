# ai-debate

Adversarial truth-seeking through structured AI debates.

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
- Support for all 5 models (Claude, GPT-4, GPT-3.5, Gemini, Grok)

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
- [ ] add chatGPT, grok, gemini, et al.; assess how different LLMs do, perhaps depending on the nature of the debate -- particularly the political leanings of the sides that the LLMs are instructed to defend.
- [ ] allow the input of an entire news article, either in plain text or as a website. in this case, the first step is to extract specific claims; then, those are fed into the above pipeline.
- [ ] weight sources according to credibility, e.g. ranging from government websites and reuters down towards blog posts and news sources that are known to be politically biased.
- [ ] have multiple judges (a "mixture of experts"); average their scores, or have another judge that synthesizes their scores.
- [ ] save all the data (including metadata such as the topic of debate), and try to extract specific learnings -- about debates in general (e.g. first-mover dis/advantage), varying sources, and specific LLMs.
- [ ] make this into a webpage, where a user can input their own claim or news article (and probably their own API key(s)).
- [ ] add an RL policy that learns which actions lead to higher final scores (depending on various hyperparameters such as the costs of various citations). this can be a single policy that updates after debates against a frozen opponent, or ideally multiple policies that learn through self-play.