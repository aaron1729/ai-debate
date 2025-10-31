# Debate Podcast Data

This directory contains real-world debate data from three prominent debate series:
- **Munk Debates** - High-profile debates on major global issues
- **Open To Debate** - Debates on current affairs and policy questions
- **Soho Forum** - Libertarian-oriented Oxford-style debates

## Data Structure

### Raw Data (`raw/`)
Contains the original CSV files with debate results:
- `Munk-Debates.csv`
- `Open-To-Debate.csv`
- `Soho-Forum-Debates.csv`

Each CSV includes:
- Debate motion/resolution
- Date
- Pre-debate voting percentages (For/Against)
- Post-debate voting percentages (For/Against)
- Vote swing (showing which side was more persuasive)
- Winner determination (based on who changed more minds)

### Processed Data
The processed JSON file (`data/debate_motions.json`) contains all debate motions in a standardized format:

```json
{
  "motion": "The standalone debatable claim/resolution",
  "date": "ISO 8601 timestamp",
  "source": "Munk Debates|Open To Debate|Soho Forum",
  "sourceUrl": null,
  "preVote": {
    "for": 50.0,
    "against": 50.0
  },
  "postVote": {
    "for": 34.0,
    "against": 66.0
  },
  "voteSwing": {
    "pro": -16.0
  },
  "winner": "For|Against|Draw",
  "type": "debate_motion",
  "topic": "politics|economics|health|technology|etc."
}
```

## Processing the Data

To regenerate the processed JSON file:

```bash
python process_debate_podcasts.py data/debate-podcasts/raw/ -o data/debate_motions.json --model claude
```

Options:
- `--model claude|gpt4|...` - Use an LLM to assign topics (default: none, assigns "general")
- `--topics-file topics.json` - Topics file to use/update (default: topics.json)

Without a model, all motions will be assigned the topic "general".

## How This Differs from Fact-Checked Claims

**Important distinction:** This data represents real debate outcomes, not fact-checking results.

### Debate Motions vs. Fact-Checked Claims

| Aspect | Debate Motions | Fact-Checked Claims |
|--------|---------------|---------------------|
| **Source** | Debate podcasts/series | Fact-checking organizations |
| **Evaluation** | Persuasiveness (vote swing) | Truth value (verdict) |
| **Outcome** | Winner (who changed more minds) | Verdict (supported/contradicted/etc.) |
| **Data** | Pre/post voting percentages | Claim date, publisher, URL |
| **Purpose** | Test persuasion strategies | Test truth evaluation |

**Key insight:** A debate "won" by the "For" side doesn't mean the claim is true—it means the For side was more persuasive in that particular debate.

## Use Cases

### For AI Debate Experiments

Debate motions can be used as:

1. **Test claims for debate experiments** - These are already well-formulated, standalone, debatable propositions
2. **Comparison data** - Compare AI debate outcomes to real human debate outcomes
3. **Persuasion benchmarks** - See if AI debates produce similar vote swings to human debates

### Topic Distribution

Current breakdown (as of last processing):
- Politics: 26 motions
- Economics: 4 motions
- Health: 3 motions
- Technology: 3 motions
- Religion: 1 motion

## Data Quality Notes

- Some motions have incomplete voting data (marked with `null` values)
- Dates are normalized to ISO 8601 format
- Some dates only have year precision (defaulted to January 1st)
- Vote swings can be positive (For side gained) or negative (Against side gained)
- "Draw" outcomes are rare but possible (no vote swing)

## Integration with Existing Claims Data

Debate motions are stored separately from fact-checked claims to preserve their unique characteristics:

- **Fact-checked claims**: `data/claims_verified_*.json`
  - Schema: claim, claimDate, publisher, url, verdict, topic
  - Purpose: Truth evaluation

- **Debate motions**: `data/debate_motions.json`
  - Schema: motion, date, source, sourceUrl, preVote, postVote, voteSwing, winner, type, topic
  - Purpose: Persuasion evaluation

Both datasets share the `topic` field for categorization, allowing experiments to sample from either dataset or a combination of both.

## Future Enhancements

Potential additions:
- Source URLs for each debate (currently null)
- Debater names/profiles
- Audience demographics
- Debate format details
- Video/audio links to actual debates
