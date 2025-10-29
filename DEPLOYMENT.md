# Deployment Guide: AI Debate System

This guide walks you through deploying the AI Debate System to Vercel.

## Prerequisites

- GitHub account
- Vercel account (sign up at https://vercel.com)
- Upstash account for Redis rate limiting (free tier available)
- API keys for at least one LLM provider (optional for free tier)

## Deployment Architecture

The system offers two usage modes:

1. **Free Tier**: 5 debates per IP per 24 hours using your API keys
2. **Unlimited**: Users provide their own API keys (stored only in browser)

## Step-by-Step Deployment

### Step 1: Set Up Upstash Redis (Required)

Rate limiting requires a Redis database to track usage per IP address.

1. Go to https://upstash.com/
2. Sign up or log in (free tier available)
3. Click **"Create Database"**
4. Configure:
   - **Type**: Regional (free tier)
   - **Region**: Choose closest to your users (e.g., us-east-1)
   - **Name**: `ai-debate-ratelimit`
5. Click **"Create"**
6. After creation, go to the **REST API** tab and copy:
   - `UPSTASH_REDIS_REST_URL`
   - `UPSTASH_REDIS_REST_TOKEN`

Keep these values handy - you'll need them in Step 4.

### Step 2: Install Dependencies & Test Locally (Recommended)

Before deploying, verify everything works locally:

```bash
# Install Node.js dependencies
npm install

# Create local .env file
cp .env.example .env
# Edit .env and add your API keys and Upstash credentials

# Build the project
npm run build

# Test locally
npm run dev
```

Visit http://localhost:3000 to test the application.

### Step 3: Push Code to GitHub

If you haven't already pushed your latest changes:

```bash
git add .
git commit -m "Add web deployment with rate limiting"
git push origin main
```

### Step 4: Deploy to Vercel

#### 4.1 Import Project

1. Go to https://vercel.com/
2. Sign in with GitHub
3. Click **"New Project"**
4. Find and import your repository: `ai-debate`
5. Vercel will auto-detect it's a Next.js project

#### 4.2 Configure Environment Variables

**BEFORE clicking Deploy**, add environment variables:

Click **"Environment Variables"** and add these:

**Required (for rate limiting):**
```
UPSTASH_REDIS_REST_URL=your_upstash_url_from_step_1
UPSTASH_REDIS_REST_TOKEN=your_upstash_token_from_step_1
```

**Optional (for free tier - add only the models you want to provide):**
```
ANTHROPIC_API_KEY=sk-ant-xxxxx
OPENAI_API_KEY=sk-xxxxx
GOOGLE_API_KEY=AIzaSyxxxxx
XAI_API_KEY=xai-xxxxx
```

**Optional (admin rate limiting):**
```
ADMIN_IP=your.ip.address.here
ADMIN_RATE_LIMIT=500
```

Notes:
- You only need to add keys for models you want users to access for free
- If you don't add any LLM API keys, users must provide their own
- Consider your budget: each free debate consumes API tokens
- To find your IP address: `curl https://api.ipify.org`
- The ADMIN_IP will get ADMIN_RATE_LIMIT uses per model per day (default: 500)
- Other IPs get 5 uses per model per day

#### 4.3 Deploy

1. Click **"Deploy"**
2. Wait 2-3 minutes for initial deployment
3. You'll get a URL like: `https://ai-debate-xxxx.vercel.app`

## How It Works

### Free Tier (With Your API Keys)

When you provide API keys in Vercel environment variables:
- Users get 5 free debates per 24 hours
- Rate limited by IP address using Upstash Redis
- After 5 debates, they see a message to provide their own keys
- Rate limit resets after 24 hours

### Unlimited Usage (User-Provided Keys)

Users can click **"Show API Keys (optional)"** on the website to:
- Enter their own API keys
- Get unlimited debates
- Keys are stored only in their browser (never on your server)
- No rate limiting applies

### API Request Flow

1. User submits debate request
2. System checks if using server keys or user keys
3. If server keys: Check rate limit in Redis
4. If rate limit exceeded: Return 429 error
5. If ok: Run debate and return results

## Cost Considerations

### Your Costs

**Vercel (Free Tier):**
- 100GB bandwidth/month
- Unlimited deployments
- Serverless function executions: Plenty for moderate traffic

**Upstash Redis (Free Tier):**
- 10,000 commands/day
- 256 MB storage
- Good for ~10,000 debate requests/day

**LLM API Costs (Only if you provide keys for free tier):**
- Each debate = ~4 API calls (2 debaters × 2 turns + 1 judge)
- Claude Sonnet 4.5: ~$0.03-0.15 per debate (depending on length)
- GPT-4: ~$0.06-0.30 per debate
- Gemini/GPT-3.5: ~$0.001-0.01 per debate

**Example monthly cost:**
- 100 free debates/month using Claude: ~$3-15
- 500 free debates/month using GPT-3.5: ~$0.50-5

### User Costs

- **Free**: 5 debates per day using your keys
- **Paid**: Bring their own API keys for unlimited usage

## Post-Deployment

### Testing Your Deployment

1. Visit your Vercel URL
2. Run a test debate (uses your free tier)
3. Test rate limiting:
   - Run 5 debates to use your quota
   - 6th debate should show rate limit error
4. Test user-provided keys:
   - Click "Show API Keys"
   - Enter valid API keys
   - Should bypass rate limiting

### Monitoring Usage

**Vercel Dashboard:**
- Function invocations
- Bandwidth usage
- Error rates
- Visit: https://vercel.com/dashboard

**Upstash Dashboard:**
- Request count
- Rate limit hits
- Database size
- Visit: https://console.upstash.com/

**API Provider Dashboards:**
- Token usage and costs
- Rate limits
- Anthropic: https://console.anthropic.com/
- OpenAI: https://platform.openai.com/usage
- Google: https://aistudio.google.com/

### Custom Domain (Optional)

To use your own domain:

1. Go to your Vercel project
2. Settings → Domains
3. Add your domain (e.g., `aidebate.yourdomain.com`)
4. Follow DNS configuration instructions

## Updating Your Deployment

Vercel automatically redeploys on every push to main:

```bash
# Make your changes
git add .
git commit -m "Update debate prompts"
git push origin main
```

Deployment happens automatically in ~2 minutes.

### Updating Environment Variables

To change API keys or other variables:

1. Go to Vercel project settings
2. Settings → Environment Variables
3. Edit or add variables
4. Click **"Redeploy"** to apply changes

## Troubleshooting

### Build Fails

**Error: Module not found**
```bash
# Locally, verify dependencies
npm install
npm run build
```

**TypeScript errors**
- Check `lib/debate-engine.ts` and `pages/` for type errors
- Run `npm run build` locally to see detailed errors

### Rate Limiting Not Working

**Symptoms**: Users can run unlimited debates with server keys

**Fixes**:
1. Verify Upstash environment variables are set correctly
2. Check Upstash dashboard - is it receiving requests?
3. Look at Vercel function logs for errors

### API Errors

**"API key required"**
- User needs to provide their own keys if you don't have server keys
- Or add API keys to Vercel environment variables

**"404 model not found"**
- Model ID may be deprecated (check `lib/debate-engine.ts`)
- Update to current model IDs

### High Costs

If your API costs are too high:

1. **Reduce free tier**:
   - Edit `pages/api/debate.ts`
   - Change `slidingWindow(5, '24 h')` to `slidingWindow(3, '24 h')`

2. **Remove expensive models**:
   - Remove GPT-4 API key from Vercel
   - Keep only GPT-3.5 or Gemini for free tier

3. **Disable free tier entirely**:
   - Remove all LLM API keys from Vercel
   - Users must provide their own keys

## Security Notes

### API Key Safety

**Your keys (server-side)**:
- ✅ Stored in Vercel environment variables
- ✅ Never exposed to client
- ✅ Only used in API routes

**User keys (client-side)**:
- ⚠️ Stored in browser memory only
- ⚠️ Never sent to your server for storage
- ⚠️ Users responsible for their own keys

### Rate Limiting

- IP-based rate limiting via `x-forwarded-for` header
- Vercel provides accurate IP addresses
- Redis sliding window prevents gaming the system

### CORS & Security Headers

Next.js API routes are protected by default. No additional configuration needed.

## Support

**Issues with this project:**
- GitHub Issues: https://github.com/aaron1729/ai-debate/issues

**Platform-specific help:**
- Vercel: https://vercel.com/docs
- Upstash: https://docs.upstash.com/
- Next.js: https://nextjs.org/docs

## Summary Checklist

- [ ] Upstash Redis database created
- [ ] UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN copied
- [ ] Code tested locally with `npm run build` and `npm run dev`
- [ ] Latest code pushed to GitHub
- [ ] Project imported to Vercel
- [ ] Environment variables added to Vercel
- [ ] Deployment successful
- [ ] Test debate completed on live site
- [ ] Rate limiting tested (if using free tier)
- [ ] Monitoring dashboards bookmarked

Congratulations! Your AI Debate System is now live.
