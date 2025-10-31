# Changelog

## 2025-10-30 - Debate Podcast Data Integration

### Added

**New Script: `process_debate_podcasts.py`**
- Converts CSV files from debate podcasts into standardized JSON format
- Processes data from three debate series: Munk Debates, Open To Debate, Soho Forum
- Uses LLM to assign topics (same topic list as fact-checked claims)
- Outputs 37 debate motions with pre/post voting data and winners

**New Data: `data/debate_motions.json`**
- 37 real-world debate motions from professional debate series
- Includes pre/post debate voting percentages, vote swing, winner determination
- Topic distribution: Politics (26), Economics (4), Health (3), Technology (3), Religion (1)

**New Documentation: `data/debate-podcasts/README.md`**
- Complete guide to debate podcast data structure
- Explains key distinction between fact-checked claims (truth evaluation) vs debate motions (persuasiveness evaluation)
- Usage examples and processing instructions
- Integration notes with existing experiment infrastructure

**Raw Data Sources**
- `data/debate-podcasts/raw/Munk-Debates.csv` - 18 motions
- `data/debate-podcasts/raw/Open-To-Debate.csv` - 7 motions with voting data
- `data/debate-podcasts/raw/Soho-Forum-Debates.csv` - 12 motions

### Modified

**Updated `README.md`**
- Added debate_motions.json to ready-to-use claims list
- Documented debate podcast data sources and structure
- Explained distinction between truth evaluation (fact-checks) and persuasiveness (debates)
- Added processing command and use cases

**Updated `docs/claude.md`**
- Added debate podcast data integration to implemented features
- New section: "Debate Podcast Data Integration" with complete implementation details
- Updated file structure to include process_debate_podcasts.py and data organization
- Added debate_motions.json to data directory listing

**Updated `topics.json`**
- Added "religion" topic (from "religion is a force for good" debate motion)

### Completed TODO Items

- ✅ "use claims and results from debate podcasts as data" (removed from README.md TODO list)

### Key Design Decisions

**Parallel Data Structure**
- Debate motions stored separately from fact-checked claims to preserve unique characteristics
- Both share `topic` field for categorization
- Allows experiments to sample from either dataset or combination
- Maintains distinction: truth (fact-checks) vs persuasiveness (debates)

**Data Schema**
```json
{
  "motion": "Standalone debatable claim",
  "date": "ISO 8601 timestamp or null",
  "source": "Debate series name",
  "sourceUrl": null,
  "preVote": {"for": 50.0, "against": 50.0},
  "postVote": {"for": 34.0, "against": 66.0},
  "voteSwing": {"pro": -16.0},
  "winner": "For|Against|Draw",
  "type": "debate_motion",
  "topic": "assigned topic"
}
```

### Use Cases

1. **Benchmark AI debates** against real human debate outcomes
2. **Compare vote swings**: Do AI debates produce similar persuasion patterns?
3. **Test persuasion strategies**: Which arguments work in real vs AI debates?
4. **Validate judge verdicts**: Do AI judges align with human audience voting?

### Processing Command

```bash
python process_debate_podcasts.py data/debate-podcasts/raw/ -o data/debate_motions.json --model claude
```

### Future Enhancements

Potential additions to debate podcast data:
- Source URLs for each debate (currently null)
- Debater names and profiles
- Audience demographics
- Debate format details
- Video/audio links to actual debates
