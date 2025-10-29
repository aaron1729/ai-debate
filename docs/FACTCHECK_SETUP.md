# Google Fact Check Tools API Setup

This guide shows how to use the Google Fact Check Tools API to fetch claims for testing the debate system.

## Purpose

We use the Google Fact Check Tools API to:
1. Fetch real fact-checked claims from professional fact-checkers
2. Run debates on these claims using our AI debate system
3. Compare our verdicts with professional fact-checker ratings
4. Analyze system performance and identify biases

## Quick Setup

The Fact Check Tools API is **very simple** - it only requires an API key (no service account needed).

### 1. Enable the API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create one)
3. Go to [Fact Check Tools API](https://console.cloud.google.com/apis/library/factchecktools.googleapis.com)
4. Click **"Enable"**
5. Wait a few minutes for it to propagate

### 2. Get an API Key

**If you already have a Google API key** (e.g., for Gemini), you can reuse it:

1. Go to [Credentials](https://console.cloud.google.com/apis/credentials)
2. Find your existing API key
3. Click "Edit"
4. Under "API restrictions" → "Restrict key"
5. Make sure **"Fact Check Tools API"** is checked
6. Save

**If you need a new API key:**

1. Go to [Credentials](https://console.cloud.google.com/apis/credentials)
2. Click **"Create Credentials"** → **"API key"**
3. Copy the API key
4. (Optional but recommended) Click "Restrict Key" and select only the APIs you need

### 3. Add to Environment

Your `.env` file should already have `GOOGLE_API_KEY` (used for Gemini). The fact-check script uses the same key:

```bash
GOOGLE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

That's it! No service account needed.

## Usage

### Fetch Claims

Run the fetch script:

```bash
source venv/bin/activate
python fetch_claims.py
```

This fetches claims from the last 30 days with query "the" (broad search) and saves to `claims_data.json`.

### Customize Fetching

Edit `fetch_claims.py` or call the function directly:

```python
from fetch_claims import fetch_claims, save_claims

# Fetch climate claims from last year
claims = fetch_claims(
    max_age_days=365,
    page_size=10,          # Keep at 10-20 (max supported)
    query='climate',       # Required: search term
    language_code='en'     # Recommended for clean results
)

save_claims(claims, 'my_claims.json')
```

### Fetch Multiple Topics

```python
# Fetch diverse claims across multiple topics
topics = ['health', 'climate', 'election', 'science']
all_claims = []

for topic in topics:
    claims = fetch_claims(max_age_days=180, query=topic)
    all_claims.extend(claims)

# Deduplicate
unique_claims = []
seen = set()
for claim in all_claims:
    text = claim.get('text', '')
    if text and text not in seen:
        seen.add(text)
        unique_claims.append(claim)

save_claims(unique_claims[:100], 'diverse_100.json')
```

## API Parameters

**Required:**
- `query`: Search term (e.g., "vaccine", "climate", "election")
  - Cannot be empty string
  - OR use `reviewPublisherSiteFilter` instead (e.g., "politifact.com")

**Recommended:**
- `languageCode`: `'en'` for English (filters out non-English claims)

**Optional:**
- `maxAgeDays`: How far back to search (default: 30)
- `pageSize`: Results per page (default: 10, **keep at 10-20**, larger values trigger errors)
- `pageToken`: For pagination (handled automatically)

## Output Format

Claims are saved with this structure:

```json
{
  "fetched_at": "2025-10-29T12:34:56",
  "count": 50,
  "claims": [
    {
      "text": "Climate change is a hoax",
      "claimant": "Social media user",
      "claimDate": "2025-10-15T00:00:00Z",
      "claimReview": [
        {
          "publisher": {
            "name": "AFP Fact Check",
            "site": "factcheck.afp.com"
          },
          "url": "https://factcheck.afp.com/...",
          "title": "No, climate change is not a hoax",
          "reviewDate": "2025-10-20T00:00:00Z",
          "textualRating": "False",
          "languageCode": "en"
        }
      ]
    }
  ]
}
```

## Current Test Datasets

The project includes three pre-fetched datasets:

1. **`claims_recent_30days.json`** (6 claims)
   - Recent political claims from last 30 days
   - Query: "the"

2. **`claims_historical_health_50.json`** (50 claims)
   - Health-related claims from last year
   - Query: "health"

3. **`claims_historical_climate_50.json`** (50 claims)
   - Climate-related claims from last year
   - Query: "climate"

## Troubleshooting

### "PERMISSION_DENIED" Error

- Make sure Fact Check Tools API is **enabled** in your Google Cloud project
- Wait a few minutes after enabling for it to propagate
- Check that your API key allows the Fact Check Tools API

### "Invalid request, must have either query or filter"

- You must provide a `query` parameter (cannot be empty string)
- Example: `query='climate'` or `query='health'`
- Or use `reviewPublisherSiteFilter='politifact.com'` instead

### "Request contains an invalid argument"

- Likely `pageSize` is too large - keep it at 10-20
- Or check that `maxAgeDays` is a positive integer

### "Service Unavailable" (503)

- The API sometimes returns this after fetching many pages
- This is normal - just use the data fetched so far
- Try again later or with a smaller `maxAgeDays`

### Small Number of Results

- The API doesn't have many claims for all queries
- Try:
  - Broader query terms ("the", "is", "has")
  - Longer time ranges (`maxAgeDays=365`)
  - Multiple queries and combine results
  - Different topics ("health", "climate", "politics")

## API Limits & Cost

**Cost:** FREE (no charges for read-only claims search)

**Quotas:**
- Check [Google Cloud Console Quotas](https://console.cloud.google.com/apis/api/factchecktools.googleapis.com/quotas)
- Default quotas are sufficient for research use
- If you hit limits, request a quota increase

## Important Notes

### Why Not Service Accounts?

You might see references to service accounts in Google Cloud docs. **Don't use them for this API.**

- Service accounts are for the `pages.*` write endpoints (creating/managing your own ClaimReview pages)
- The `claims:search` endpoint (what we use) requires **API key authentication only**
- Service account tokens will give 401/403 errors

### API Key vs Service Account

| Method | Used For | Works with claims:search? |
|--------|----------|--------------------------|
| API Key | Reading claims | ✅ Yes (use this!) |
| Service Account | Writing ClaimReview pages | ❌ No (not needed) |

## Next Steps

After fetching claims, you can:

1. **Run debates** on a subset of claims using `debate.py`
2. **Compare verdicts** between your system and professional fact-checkers
3. **Analyze patterns:**
   - Which types of claims are harder to evaluate?
   - Do certain models perform better on certain topics?
   - Where does your system agree/disagree with fact-checkers?
4. **Test your hypothesis:** Does debate length affect verdict accuracy?

See [claude.md](claude.md) for the full research roadmap.

## Resources

- [Fact Check Tools API Documentation](https://developers.google.com/fact-check/tools/api)
- [API Reference](https://developers.google.com/fact-check/tools/api/reference/rest/v1alpha1/claims/search)
- [Google Cloud Console](https://console.cloud.google.com/)
- [Fact Check Explorer](https://toolbox.google.com/factcheck/explorer) (web UI for the same data)
