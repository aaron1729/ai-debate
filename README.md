# ai-debate



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