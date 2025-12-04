# LLMHive Environment Setup Guide

This document describes all environment variables needed to run LLMHive.

## Frontend (Next.js on Vercel)

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ORCHESTRATOR_API_BASE_URL` | URL of the LLMHive backend API | `https://llmhive-orchestrator-xxx.run.app` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LLMHIVE_API_KEY` | API key for backend authentication | None |
| `NEXT_PUBLIC_API_BASE_URL` | Alternative to ORCHESTRATOR_API_BASE_URL | None |

## Backend (FastAPI on Cloud Run)

### Required Variables (at least ONE provider key)

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key for GPT models |
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude models |
| `GEMINI_API_KEY` | Google AI API key for Gemini models |
| `GROK_API_KEY` | xAI API key for Grok models |
| `DEEPSEEK_API_KEY` | DeepSeek API key |

> **Note:** At least one provider key must be set. Without any keys, the backend will fail to start.

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `API_KEY` | Key to authenticate incoming requests | None (unauthenticated) |
| `PINECONE_API_KEY` | Pinecone for vector memory | None |
| `PINECONE_ENVIRONMENT` | Pinecone environment | `us-west1-gcp` |
| `PINECONE_INDEX_NAME` | Pinecone index name | `llmhive-memory` |
| `STRIPE_SECRET_KEY` | Stripe for billing | None |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook verification | None |

## Local Development Setup

1. **Create `.env.local`** in the project root:

```bash
# Frontend (required)
ORCHESTRATOR_API_BASE_URL=http://localhost:8000

# Optional: API key if backend requires authentication
LLMHIVE_API_KEY=your-dev-api-key
```

2. **Backend environment** (set in terminal or `.env` in llmhive folder):

```bash
# At least one provider
export OPENAI_API_KEY=sk-...

# Optional
export API_KEY=your-dev-api-key
```

## Vercel Deployment

1. Go to Vercel Dashboard → Your Project → Settings → Environment Variables
2. Add these variables:

| Name | Value | Environment |
|------|-------|-------------|
| `ORCHESTRATOR_API_BASE_URL` | Your Cloud Run URL | Production |
| `LLMHIVE_API_KEY` | Your API key | Production |

## Cloud Run Deployment

Set environment variables in Cloud Run:

```bash
gcloud run services update llmhive-orchestrator \
  --set-env-vars="OPENAI_API_KEY=sk-...,ANTHROPIC_API_KEY=sk-ant-...,API_KEY=your-key"
```

## Troubleshooting

### "Backend not configured" error
- Ensure `ORCHESTRATOR_API_BASE_URL` is set in Vercel
- Check that the value doesn't have a trailing slash

### "No provider API keys configured" error
- Set at least one provider API key on Cloud Run
- Verify the key is valid and has quota

### Settings not persisting
- Settings are stored in cookies (client-side) and localStorage
- Clear browser data if settings seem stuck
- Check browser's cookie settings

## Security Notes

- Never commit API keys to git
- Use Vercel's environment variable encryption
- Rotate keys periodically
- Use separate keys for development and production
