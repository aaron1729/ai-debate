# Documentation

This folder contains detailed documentation for the AI Debate System.

## Files

### [CLAUDE.md](CLAUDE.md)
**Implementation Context and Design Decisions**

Complete technical documentation including:
- Current implementation status
- Architecture and file structure
- Core components (CLI, web UI, debate engine)
- Design decisions with explanations
- Known issues and troubleshooting
- Development tips and testing guidance
- Model configuration
- Rate limiting implementation
- Test data integration with Google Fact Check API

**Audience**: Developers working on the codebase, future contributors, AI assistants

**When to read**: Before making changes, when debugging issues, to understand design rationale

### [DEPLOYMENT.md](DEPLOYMENT.md)
**Vercel Deployment Guide**

Step-by-step instructions for deploying the web UI to Vercel:
- Environment variable setup
- Upstash Redis configuration
- Rate limiting setup
- Admin IP privileges
- Deployment steps
- Testing and verification

**Audience**: Developers deploying to production

**When to read**: When ready to deploy to Vercel (after fixing rate limit bug)

### [FACTCHECK_SETUP.md](FACTCHECK_SETUP.md)
**Google Fact Check Tools API Setup**

Guide for fetching real fact-checked claims to test the debate system:
- API setup (API key, not service account)
- Quick start instructions
- Fetching claims with custom parameters
- Understanding the data format
- Current test datasets
- Troubleshooting common errors
- API limits and costs

**Audience**: Researchers, developers testing the system

**When to read**: When you want to fetch new test claims or understand existing datasets

## Quick Links

**For new developers**: Start with [CLAUDE.md](CLAUDE.md) to understand the architecture

**For deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md) (but note rate limiting bug must be fixed first)

**For testing with real data**: See [FACTCHECK_SETUP.md](FACTCHECK_SETUP.md) to fetch fact-checked claims

**For project overview**: See [../README.md](../README.md) for vision and roadmap
