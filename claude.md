# Claude.md - Implementation Context

This file provides implementation details and design decisions for the AI Debate System to help future development.

## Project Overview

An adversarial truth-seeking system that uses AI debate to evaluate factual claims. Two AI agents argue opposing sides while a judge evaluates the evidence presented.

**Core Hypothesis**: As debate length increases, verdicts should stabilize toward truth. Misleading arguments are more likely to succeed in shorter debates.

## Current Status (MVP)

**Implemented:**
- ✅ CLI script with configurable turn counts (1, 2, 4, 6)
- ✅ Two debater agents (Pro/Con) using Claude 3 Opus
- ✅ Judge agent that assigns verdicts (supported/contradicted/misleading/needs more evidence)
- ✅ Structured refusal handling (models can refuse in JSON format)
- ✅ Proper API error handling vs refusal detection
- ✅ Console output formatting
- ✅ Debate shortening when refusals occur

**Not Yet Implemented:**
- ⏳ Web scraping/verification of cited sources
- ⏳ Multiple LLM support (GPT, Gemini, etc.)
- ⏳ Persistent storage/database
- ⏳ Source credibility weighting
- ⏳ Multiple judges ("mixture of experts")
- ⏳ RL policy learning

## Architecture

### File Structure
```
/
├── debate.py          # Main script with all logic
├── requirements.txt   # anthropic, python-dotenv
├── .env              # ANTHROPIC_API_KEY (gitignored)
├── .env.example      # Template
├── tmp.py            # Test script for API/model validation
├── README.md         # Project vision and roadmap
└── claude.md         # This file
```

### Core Components

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

**Implementation**: See debate.py:165-176

### 2. Debate History Filtering

**Key Insight**: When one side refuses, opponent shouldn't know about it.

**Implementation** (debate.py:108-119):
- Refusals are filtered out when building debate history for opponent
- Opponent sees empty history and argues as if going first
- This prevents "arguing against a refusal" confusion

**Why**: Preserves adversarial structure even with asymmetric participation.

### 3. Error Handling Hierarchy

**Three distinct error types**:

1. **RuntimeError**: API failures (network, auth, rate limits)
   - Caught from Anthropic client exceptions
   - Clear user message, exit debate

2. **ValueError**: Malformed responses (bad JSON, missing fields)
   - Model returned text but not valid debate format
   - Clear user message, exit debate

3. **Structured Refusal**: Model explicitly refuses (not an error)
   - Valid JSON with `"refused": true`
   - Continue debate with opponent
   - Record as data in transcript

**Implementation**: See debate.py:131-190, 354-398

### 4. Role Clarity for Debaters

**Problem**: Ambiguous phrasing like "argue against this claim" confused models about their task.

**Solution** (debate.py:37-50):
- Pro: "argue that this claim IS TRUE" / "SUPPORTING the claim"
- Con: "argue that this claim IS FALSE or MISLEADING" / "CONTRADICTING or DEBUNKING the claim"

**Result**: Con side now correctly understands they should debunk false claims, not refuse.

### 5. Emphatic Participation Instructions

**Challenge**: Need to discourage refusals while keeping option available for ethics research.

**Approach** (debate.py:60-71):
- "STRONGLY EXPECTED to participate"
- Multiple analogies (defense attorney, academic debater, devil's advocate)
- Frame refusal as undermining truth-seeking
- Still explicitly allow refusal for "extreme ethical concerns"

**Balance**: Strong encouragement + escape hatch for genuine ethical issues.

## Model-Specific Notes

### Current Model: Claude 3 Opus (claude-3-opus-20240229)

**Why this model**:
- Only Claude model accessible with available API key during development
- Deprecated (EOL January 2026) but functional
- Most capable of Claude 3 family

**Known behavior**:
- Still refuses some controversial claims even with strong prompting
- Particularly sensitive to claims about specific named individuals
- Generally willing to debate ideas/policies/factual claims

**Future migration**:
- Should use Claude 3.5 Sonnet (better performance, lower cost)
- Test with multiple models to compare refusal rates
- Model comparison is a key research direction (see README extensions)

## Testing Guidance

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
- "Charlie Kirk was a menace to society" → Both sides refused

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

## Development Tips

### Adding New Features

**To add a new LLM provider**:
1. Create new class similar to `Debater` with different client
2. Update `run_debate()` to accept model parameter
3. Handle provider-specific error types
4. Test refusal behavior (may differ significantly)

**To save debate data**:
1. Add file/database writing to `run_debate()` after verdict
2. Include metadata: timestamp, model, claim, turn count, verdict
3. Store full debate history as JSON
4. Consider privacy implications of storing API responses

**To verify citations**:
1. Add URL fetching in `make_argument()` before returning
2. Check if quote appears in fetched content
3. Flag suspicious citations in debate history
4. Handle errors gracefully (may be paywalled, etc.)

### Common Issues

**"No JSON found in response"**:
- Model returned plain text instead of JSON
- Check if model is refusing (should use structured format now)
- May indicate prompt confusion - review system prompt

**Both sides refuse**:
- Claim may be too controversial for current model
- Try rephrasing as idea/policy rather than person
- Consider testing with different model

**Con side argues wrong position**:
- Check role description clarity (debate.py:37-50)
- Ensure "CONTRADICTING or DEBUNKING" language is clear

## Future Considerations

### When Adding Multi-Model Support

**Key questions**:
- How to handle different refusal rates across models?
- Should Pro and Con use same model or different models?
- How to compare model performance fairly?

**Data to collect**:
- Refusal rates by model and claim type
- Verdict distributions by model
- Correlation between debate length and verdict stability

### When Adding Persistent Storage

**What to store**:
- Full debate transcripts (including refusals)
- Metadata: model, timestamp, turn count, verdict
- User-provided claim + any ground truth labels
- Source URLs and quotes (for future verification)

**Analysis possibilities**:
- First-mover advantage/disadvantage
- Verdict stability vs turn count (test core hypothesis)
- Model-specific biases in refusals
- Source quality correlation with verdicts

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
- Uses python-dotenv to load from .env file
- API key required, script exits if not found
- .env is gitignored

**Production considerations**:
- Add support for environment variable fallback
- Implement rate limiting/quota management
- Add retry logic with exponential backoff for transient errors
- Consider cost tracking (tokens used per debate)

## Contributing

When modifying the system, please:
1. Update this file if architecture changes
2. Test with various claim types (factual, misleading, controversial)
3. Check both successful debates and refusal handling
4. Verify error messages are clear and actionable
5. Consider implications for research hypothesis

## Resources

- Anthropic API docs: https://docs.anthropic.com/
- Model deprecation schedule: https://docs.anthropic.com/en/docs/resources/model-deprecations
- Claude 3 model comparison: https://docs.anthropic.com/en/docs/about-claude/models
