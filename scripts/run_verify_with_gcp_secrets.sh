#!/usr/bin/env bash
# Load llmhive-orchestrator secrets and run provider connectivity audit.
set -euo pipefail

PROJECT="${GCP_PROJECT:-llmhive-orchestrator}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

load() {
  local env=$1 secret=$2
  if val=$(gcloud secrets versions access latest --secret="$secret" --project="$PROJECT" 2>/dev/null); then
    export "$env=$val"
  fi
}

load OPENAI_API_KEY openai-api-key
load ANTHROPIC_API_KEY anthropic-api-key
load GROK_API_KEY grok-api-key
load GEMINI_API_KEY gemini-api-key
load GOOGLE_AI_API_KEY gemini-api-key
load GEMINI_API_KEY_2 gemini-api-key-2
load DEEPSEEK_API_KEY deepseek-api-key
load TOGETHERAI_API_KEY togetherai-api-key
load OPENROUTER_API_KEY open-router-key
load GROQ_API_KEY groq-api-key
load CEREBRAS_API_KEY cerebras-api-key
load FIREWORKS_KEY fireworks-key
load FIREWORKS_MODELS fireworks-models
load HYPERBOLIC_KEY Hyperbolic-key
load HYPERBOLIC_MODELS hyperbolic-models
load HYPERBOLIC_BASE_URL hyperbolic-base-url
load DeepInfra_Api_Key deepInfra_api_key
load DASHSCOPE_API_KEY dashscope-api-key
load DASHSCOPE_BASE_URL Dashscope-base-url
load Cloudflare_Api_Key cloudflare-api-key
load Cloudflare_Account_ID cloudflare-account-id
load Kimi_K26_Api_Key kimi-k26-api-key
load AZURE_FOUNDRY_API_KEY azure-foundry-api-key
load AZURE_FOUNDRY_ENDPOINT azure-foundry-endpoint
load AZURE_FOUNDRY_DEPLOYMENTS azure-foundry-deployments

exec python3 "${ROOT}/scripts/verify_direct_providers.py" "$@"
