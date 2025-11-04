# AI Debate in 2025

<p align="center">
  <a href="https://ai-debate-4-u.vercel.app/">
    <img src="public/hero/ai-debate-display-2400x1260-rounded.png" alt="AI Debate Hero" width="400" style="max-width: 100%; height: auto;">
  </a>
</p>


# TO DO

- [ ] finish writeup
- [ ] add ToC


## Overview

We implement [AI Safety via Debate](https://arxiv.org/abs/1805.00899) (Irving et al., 2018), a proposed mechanism for AI alignment, within the context of natural language debates between LLMs. This comprises the following steps, which are each elaborated upon in more detail below.
- We implement an end-to-end pipeline for running automated debates with two LLM debaters and an LLM judge. This is pipeline is also deployed as a web app [here](https://ai-debate-4-u.vercel.app/).
- We source, clean, and verify datasets from a variety of sources:
  - the Google Fact Check Tools API;
  - direct generation via LLM;
  - debates motions from popular debate podcasts.
  Specifically, we obtain debate claims from all three of these sources, and we obtain ground-truth labels from the former two sources.
- We run 280 debates in total, and analyze the results from a number of different angles.

We begin with a brief discussion of the context for this demo project, and we conclude by enumerating some open directions for further investigation.

The code itself was primarily written in collaboration with Claude Code. The repo itself is carefully organized for further iteration, with extensive technical documentation in [`docs/`](docs/) (see particularly [docs/claude.md](docs/claude.md)). Please feel free to experiment and make a PR!

## Background

The 2018 paper [AI Safety via Debate](https://arxiv.org/abs/1805.00899) proposes a mechanism for AI alignment: training agents via self-play in a zero-sum debate game. It is proposed that this may be useful in contexts where a human can adequately judge the end result despite not being able to evaluate turn-by-turn performance. (This is the case with complex games like Go or Chess, and the paper draws an extensive analogy with the distinction between P and NP algorithms.) As a proof-of-concept, this is implemented within the context of a very simple "debate" game: given a handwritten digit image from the MNIST dataset, two debater models try to convince a judge model of the true label by iterative revealing pixels turn-by-turn.

The years since 2018 have seen an explosion of progress in both the power and popularity of AI models, particularly ushered in by the "ChatGPT moment" in late 2022. In particular, LLMs are now extremely well-suited to the above mechanism. However, before it can be trusted as a beneficial tool for AI alignement, it must be stress-tested in this new and qualitatively different context. Such stress-testing is the primary purpose of our experiments.

## Pipeline

A debate consists of two debaters alternating arguments for & against a given claim, followed by a judge's evaluation.

A silly example of a debate claim is "A hot dog is a type of sandwich." Another example of a debate claim is "The Holocaust happened."

Each debater is assigned a side, "pro" or "con". They are instructed to debate as strongly as possible in favor of their side (regardless of their own internal beliefs).
 In each turn, each debater is provided with the entire transcript of the debate thus far, and provides:
- evidence in the form of a URL and a quote therefrom;
- an explanation of the context for the evidence;
- an argument for their position, based on the evidence provided (and within the context of the debate thus far).

The judge is instructed to evaluate the debate, assigning both a category label and a numerical score and also providing a summary of the debate and its reasoning for its decision. The available labels are: "supported", "contradicted", "misleading", and "needs more evidence". The numerical score is an integer from 0 to 10 (inclusive), with 0 corresponding to "completely contradicted" and 10 corresponding to "completely supported"; the numerical score is `None` in the case of "needs more evidence".

The user can specify:
- the claim under debate;
- the LLMs assigned to "pro debater", "con debater", and "judge";
- the number of turns in the debate;
- whether "pro" or "con" argues first.

In case one or both of the models refuses to debate the claim, their refusal response is incorporated into the debate transcript, and the debate is sent to the judge after the turn is completed. (For example, among the LLMs that we use (Claude Sonnet 4.5, Gemini 2.5 Flash, GPT-4, and Grok 3), only Grok is willing to debate against the claim "The Holocaust happened.")

This pipeline is available both as a CLI (using [`scripts/core/debate.py`](scripts/core/debate.py)) and as a [web app](https://ai-debate-4-u.vercel.app/).

Here is an example of the above silly claim being debated via the web app.

<p align="center">
  <img src="docs/assets/hot-dog-screenshot.png" alt="Screenshot of hot dog debate." width="600" style="max-width: 100%; height: auto;">
</p>

The web app is written in TypeScript, built with Next.js, and deployed on Vercel. In order to limit developer costs, the web app features rate-limiting: each IP address receives 5 free uses per model per day, and a global backstop ensures that no model is used more than 200 times per day. An Upstash/Redis database records usage (with IP addressed hashed for safety), both to handle rate-limiting and to afford the possibility of using user-generated debates as experiment data.

## Data

As noted in [above](#overview), we source, clean, and verify datasets from a variety of sources:
1. the Google Fact Check Tools (GFCT) API;
1. direct generation via LLM;
1. debates motions from popular debate podcasts.

At a minimum, each claim consists of a claim text as well as a topic, e.g. the claim "Vaccines containing mRNA technology alter a person's DNA permanently." is tagged with the topic "health". The topics are drawn from the following list: "climate", "economics", "environment", "health", "politics", "religion", "science", "technology".

The GFCT API serves factual claims that are submitted by fact-checking organizations (e.g. PolitiFact) and accompanied by verdicts (e.g. "mostly false") and links to articles with further details. Cleaning them amounts to clarifying the claims when they are vague or imprecise, assigning ground-truth values, and labeling by topic. Verifying them amounts to checking that the linked articles indeed support the corresponding verdicts (which is not always the case).

The debate podcasts used are "Munk Debates", "Open To Debate", and "Soho Forum". These podcasts feature debates by (human) experts, who argue for and against such claims as "Anti-Zionism is anti-Semitism." These debates are evaluated by polling the audience on their opinions before and after the debate, and determining the winner based on the _change_ in audience opinion. (For instance, the audience agreement with the anti-Zionism claim rose from 61% to 66% through the debate, and so the "pro" side was decared the winner.) These debates were of course conducted within the context of their respective present moments, and so here we modify the debate claims to explicitly name this context (e.g. "As of July 2025, President Trump's deportation policies generally violated key civil liberties as set forth in the U.S. Constitution.") and we require the debaters to argue within that same context (so e.g. they cannot reference any events that have happened in the meantime).

The various raw, cleaned, and verified datasets are all stored as json files in [`data/`](/data); the cleaning and verification scripts are in [`/scripts/data_processing/`](/scripts/data_processing/). All natural language tasks (e.g. clarifying vague claims and labeling by topic) are accomplished via LLM API calls (and spot-checked for accuracy after the fact).

## Experiments




API claims weren't great, because once they're 



see database, and plots.



a hypothesis: as the debate length increases, the judge's verdict will stabilize -- presumably erring towards the truthful side (which requires human-labeled inputs). said differently, misleading arguments are more likely to win in short debates.


- have the two debaters switch sides and see how it goes [this is already happening in `run_experiments.py`]
- switch whether pro or con goes first (with all else equal). plot this.

debate-motions (no ground truth); note duplicate judging and stability (even though models have their own randomness (temperature > 0)).

for debater strength: compare the "political correctness debates", which involved _all_ six matchups (4 choose 2).


Judgments are surprisingly stable: over the 8 suites of 4 debates between the same two debaters where all judges weighed in at all turns, we have judgment correlations:
- claude: 0.87
- gemini: 0.84
- gpt-4: 0.82
- grok: 0.79
(see `plotting/plots/debate-motions/` and `plotting/plots/debate-motions-with-duplicate-judging/` for visual comparison.)

judge-debater-agreement (just violin plots) -- note particularly self-bias, refer to "implicit learning" or whatever it's called.


make & discuss more plots!!





✅ **280+ debates run** across various configurations
- Debates with varying turn counts (1, 2, 4, 6 turns)
- All 6 possible debater matchups tested (claude-gemini, claude-gpt4, claude-grok, gemini-gpt4, gemini-grok, gpt4-grok)
- Systematic 2×2 debate suites controlling for debater order and turn order
- All experiments persisted to SQLite database (`data/experiments.db`)

✅ **Key experimental findings**:
- **Judgment stability**: High correlation between duplicate judgments by same judge (0.79-0.87)
- **Convergence hypothesis**: More turns → convergence to truth for clear-cut claims (e.g., homeopathy pseudoscience: 87.5% accuracy)
- **Debater strength effects**: Strong debaters can dominate on genuinely controversial claims regardless of ground truth (e.g., minimum wage: 12.5% accuracy)
- **Judge patterns**: Claude/GPT-4 heavily use score 5 (~50-60%), Gemini is more decisive
- **Model biases**: Gemini trusts Claude, distrusts GPT-4

✅ **Comprehensive visualization suite** - 27+ plotting scripts
- 4-subplot debate motion plots showing judgment trajectories across turns
- Turn progression plots for score evolution with debate length
- Judge analysis plots (self-scoring, judge-debater agreement, judge-judge agreement)
- Histogram, violin plot, and scatterplot formats
- Publication-quality figures with color-coded models and clear legends
- Outputs in `plotting/plots/` organized by analysis type

✅ **Experiment querying and analysis tools**
- `query_experiments.py` to filter, search, and export results
- `judge_existing_debates.py` to retrospectively judge debates with different judge models
- Export to JSON for sharing and further analysis

✅ **Temporal constraints** for historical debate motions
- Automatically detects temporal framing (e.g., "As of 2019")
- Enforces that debaters/judges only use information from specified year or earlier
- Enables historically accurate debates reflecting knowledge available at the time



## Further Directions

### my notes (the rest are Claude Code)

- different models from the same provider (e.g. gpt-4 vs. gpt-5)

- label claims by how controversial they are, and by their political polarity (if any). see how debaters & judges fare.

- see if a judge appears to have an implicit bias on a given topic.

- [ ] plot ground truth on factual debate plots
- [ ] plot (or at least indicate) audience vote on debate motions plots




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

### Experiments

**Core hypothesis testing**:
- [ ] Test convergence hypothesis across more claims spanning the controversy spectrum
- [ ] Analyze first-mover advantage/disadvantage systematically
- [ ] Identify model-specific biases in refusals and argument preferences
- [ ] Compare debate verdicts with multiple fact-checker ratings

**Methodology improvements**:
- [ ] Label claims by controversy level and political polarity
- [ ] Test whether certain topics systematically favor one side
- [ ] Assess if judges have implicit biases on given topics

### Further Directions

**System enhancements**:
- [ ] Verify debaters' cited sources (URL fetching infrastructure exists, needs integration)
- [ ] Weight sources by credibility (government/Reuters → blogs/biased news)
- [ ] Multiple judges ("mixture of experts") with aggregated scores
- [ ] Extract claims from full news articles (claim extraction → debate pipeline)

**Advanced features**:
- [ ] RL policy learning through self-play
- [ ] Different model versions from same provider (e.g., GPT-4 vs GPT-5)
- [ ] Save snapshots of cited webpages for reproducibility

**Analysis**:
- [ ] Systematic comparison of debate verdicts with fact-checker ratings
- [ ] Extract learnings about debate dynamics (first-mover effects, source quality impact, model-specific patterns)
