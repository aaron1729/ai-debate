# Changelog

## 2025-11-05 - Enhanced Error Handling

### Added

**New Error Classification System** (`lib/error-handler.ts`)
- Comprehensive error categorization for all API providers (Anthropic Claude, OpenAI GPT-4, xAI Grok, Google Gemini)
- 12 error categories: `OVERLOADED`, `RATE_LIMITED`, `AUTHENTICATION`, `PERMISSION`, `NOT_FOUND`, `REQUEST_TOO_LARGE`, `TIMEOUT`, `INVALID_REQUEST`, `SAFETY_FILTER`, `INVALID_RESPONSE`, `NETWORK`, `UNKNOWN`
- User-friendly error messages with actionable suggestions
- Provider-specific error detection based on official API documentation
- Global error handler for unexpected errors

**Error Categories Implemented:**
- **Anthropic Claude**: All error types (400, 401, 403, 404, 413, 429, 500, 529 overloaded_error)
- **OpenAI GPT-4**: Authentication, rate limits, quota errors, model not found, service unavailable
- **xAI Grok**: 401, 403, 404, 429, 500/5xx errors (OpenAI-compatible)
- **Google Gemini**: Safety filter blocks, invalid arguments, rate limits, region restrictions, model not found

**Enhanced Error Response Format:**
```typescript
{
  type: 'error',
  category: 'OVERLOADED',
  provider: 'anthropic',
  model: 'Claude Sonnet 4.5',
  userMessage: 'Claude is currently experiencing high demand...',
  suggestion: 'Please wait a few minutes and try again...',
  isRetryable: true,
  completedSteps: 2
}
```

### Modified

**Updated `lib/debate-engine.ts`**
- ModelClient.generate() now catches and categorizes all API errors
- Enriched errors include categorization metadata and user-friendly messages
- Re-exports CategorizedError type for use in API routes

**Updated `pages/api/debate.ts`**
- Extracts categorized error information from enriched errors
- Sends structured error responses for both streaming and non-streaming modes
- Improved error logging with error category labels

**Updated `pages/index.tsx`**
- Changed error state from simple string to structured object with multiple fields
- Enhanced error display UI with:
  - Warning icon and error badge showing failed model
  - User-friendly error message
  - Suggestion box with actionable guidance
  - Progress indicator showing completed steps before error
  - "Try Again" button for retryable errors (only appears for transient errors)
- Improved error parsing for both streaming and non-streaming responses

**Updated `README.md`**
- Added "Error Handling" section describing comprehensive error handling features
- Documented user experience improvements for API errors

### User Experience Improvements

**Before:**
```
Error: API error (InternalServerError): 500 {"type":"error","error":{"type":"api_error","message":"Overloaded"},"request_id":null}
```

**After:**
```
⚠️ Error [Claude Sonnet 4.5]

Claude is currently experiencing high demand and cannot process your request.

Suggestion: Please wait a few minutes and try again. You can also try using a different model.

The debate completed 2 steps before this error occurred.

[Try Again] button
```

### Technical Details

**Error Detection Methods:**
- HTTP status code matching (400, 401, 403, 404, 413, 429, 500, 503, 529)
- Error type field checking (e.g., `error.type === 'overloaded_error'`)
- Error message pattern matching for provider-specific errors
- Network error code detection (ECONNREFUSED, ENOTFOUND, ETIMEDOUT)

**Retry Logic:**
- Retryable errors: `OVERLOADED`, `TIMEOUT`, `NETWORK`, `RATE_LIMITED`, `UNKNOWN`
- Non-retryable errors: `AUTHENTICATION`, `PERMISSION`, `NOT_FOUND`, `REQUEST_TOO_LARGE`, `INVALID_REQUEST`, `SAFETY_FILTER`, `INVALID_RESPONSE`

**Global Error Handler:**
- Catches all unexpected errors not categorized by provider-specific handlers
- Provides safe fallback with generic user message and technical details for debugging
- Logs errors for monitoring and troubleshooting

### Files Added
- `lib/error-handler.ts` - Complete error classification and handling system

### Files Modified
- `lib/debate-engine.ts` - Error enrichment in ModelClient
- `pages/api/debate.ts` - Structured error responses
- `pages/index.tsx` - Enhanced error UI with retry functionality
- `README.md` - Error handling documentation

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
