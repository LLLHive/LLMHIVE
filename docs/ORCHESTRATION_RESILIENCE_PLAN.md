# Orchestration Plan — Direct Connections + Aggregator Wiring

**Locked:** 2026-05-11
**Owner:** Camilo
**Goal:** Add resilience against OpenRouter throttling/outages by lighting up direct provider connections and ranked aggregator fallbacks, without regressing current behavior or quality.

> Persisted so we can revisit after account setup is complete. Update each step's status in-line as it lands.

---

## 0. Background — what we found in the audit (2026-05-10)

State of the live request path before this plan starts:

- **`Orchestrator.orchestrate`** (`llmhive/src/llmhive/app/orchestrator.py`) hard-routes every model through OpenRouter when an OpenRouter key is present. Direct providers (Google AI, DeepSeek, Grok) only execute if OpenRouter is *unavailable*, never as a primary path.
- **`EliteOrchestrator._build_model_provider_map`** (`elite_orchestration.py:1238-1242`) does the same thing for the elite paths (`parallel_race`, `best_of_n`, `expert_panel`, `challenge_refine`): when `OPENROUTER_API_KEY` is set, all models are mapped to `openrouter`. The richer `_parallel_generate` method (which actually understands multi-provider routing) is never reached from the live chat stack.
- **`ProviderRouter.PROVIDER_ROUTING`** (`provider_router.py`) does define direct routes (Groq, Google, DeepSeek, Together), but `Orchestrator.orchestrate` never calls `ProviderRouter.get_provider_for_model`. The router is only used as a *last-resort* `try_all_fallbacks` (Together → Cerebras → HuggingFace), and it does **not** include direct Google or direct DeepSeek in that chain.
- **`SAME_MODEL_PROVIDER_MATRIX`** in `provider_equivalence.py` only enumerates 9 premium SKUs with multi-provider fallbacks. Every `:free` slug falls back to `["openrouter"]` — meaning when OpenRouter throttles a free model we have **zero** secondary path.
- **Free DeepSeek slugs never hit DeepSeek direct**, even though we have a working `deepseek_client.py` and the DeepSeek API key already in Secret Manager.

**Practical implication:** under OpenRouter throttling, free-tier traffic will degrade or stall. Paid traffic has limited multi-provider failover (only the 9 premium SKUs). Latency hit from one extra hop is real on cold paths.

---

## 1. Vertex AI billing learnings (carry forward)

When evaluating "add Vertex" as a fallback for Gemini, recall:

- **Vertex AI** bills per-token like AI Studio but you also pay for the underlying compute project — egress, predictions, custom-model endpoints if any are running, even when idle.
- The cost spike Camilo experienced was almost certainly from leaving a **deployed endpoint or model serving instance running** in Vertex (per-hour charges) while expecting to pay only per-call. Vertex's deployment model ≠ AI Studio's.
- **Decision for this plan:** prefer **Google AI Studio (Gemini API)** as the direct path. If we ever want a second Gemini provider for resilience, we'll add a **second AI Studio project + key**, not Vertex. Vertex stays off unless we have a specific reason (e.g. enterprise contract, on-prem grounding) and a hard kill-switch policy.

---

## 2. The Plan — Five Phases

### Phase 1 — Verify direct connections to top-10 models (per benchmark category) + auto-replenish on billing

**Outcome:** for every model that appears in the top-10 of a benchmark we care about (reasoning, coding, math, long-context, multimodal, fast/cheap), we have a working direct connection to its first-party provider, and the billing account auto-replenishes / is on a card so it doesn't pause mid-traffic.

Top-10 first-party providers we expect to need:
- OpenAI (GPT-5.x, o-series)
- Anthropic (Claude 4.x / Opus / Sonnet / Haiku)
- Google AI Studio (Gemini 2.x / 3.x Pro/Flash/Lite)
- xAI (Grok-4 / Grok-3)
- DeepSeek (v3 / R1)
- Mistral (Large / Codestral)
- Meta (Llama 4 family — only via aggregators; no first-party API)
- Qwen / Alibaba (only via aggregators or DashScope)
- Cohere (Command-R+)
- Perplexity (Sonar series)

Tasks:
1. Build `scripts/verify_direct_providers.py` that, for each direct client we have (`openai_client`, `anthropic_client`, `google_client`, `deepseek_client`, `grok_client`, `groq_client`, `mistral_client` if present), sends a 1-token "ping" and reports `OK / 401 / 404 / timeout`.
2. For each provider, confirm in the provider's billing console that auto-replenish or auto-pay is **on**, and capture the threshold + monthly cap. Document in `docs/PROVIDER_BILLING_STATUS.md`.
3. For providers not yet wired (Mistral, Cohere, Perplexity if we want them as direct), add the client + secret and re-run the script.

Done when: green ping from every direct provider + a one-page billing status doc.

### Phase 2 — Verify current aggregators are healthy + auto-replenish

Aggregators currently configured:
- **OpenRouter** (primary today)
- **Cerebras**
- **Together AI**
- **Groq** (technically a direct provider for Llama/Mixtral but treat as aggregator-tier)
- **HuggingFace Inference**

Tasks:
1. Extend the verify script with an aggregator section: ping each aggregator's `/models` (or `/v1/models`) endpoint and one cheap chat completion.
2. Confirm billing on each: OpenRouter credit auto top-up, Together/Groq/Cerebras invoiced billing, HF subscription status.
3. Capture rate-limit headers from each ping (`x-ratelimit-*`) so we know each provider's burst budget.

Done when: aggregators all green + billing snapshot recorded.

### Phase 3 — Add new ranked aggregators (revised, cheaper, lower-risk)

Original draft proposed Vertex + multiple new aggregators. Revised to avoid Vertex billing surprises:

Add (in priority order):
1. **Fireworks AI** — strong open-weights perf, competitive pricing, broad model menu (Llama 4, Qwen, DeepSeek, Mistral, Yi).
2. **Replicate** — useful long-tail (image/multimodal), pay-per-second, easy to cap.
3. **DeepInfra** — cheapest dollars-per-1k-tokens for many open weights; good as the "spillover" tier.
4. **(Optional) A second AI Studio project + key** — gives us a second Gemini quota bucket without Vertex.
5. **(Skip for now)** Vertex AI, Bedrock — defer until we have stable revenue and a clear use case; both have non-trivial billing surface area.

Tasks:
1. Sign up + get keys, push to Secret Manager (`fireworks-api-key`, `replicate-api-key`, `deepinfra-api-key`, optional `gemini-api-key-2`).
2. Add a thin `FireworksClient`, `ReplicateClient`, `DeepInfraClient` (HTTP only — no SDK to keep build small).
3. Add ping coverage in the verify script.

Done when: at least Fireworks + DeepInfra are green and pingable.

### Phase 4 — Rank aggregators by characteristics

Rank table to drive routing weights. Columns: **latency p50**, **latency p95**, **price per 1M in/out tokens**, **rate-limit ceiling**, **uptime over last 30d**, **model coverage score (how many of our top SKUs they serve)**, **streaming quality**, **tool-call support**.

Method:
1. Use the verify script + a small load script (`scripts/aggregator_loadtest.py`, 10 sequential then 5 concurrent calls) to capture latency p50/p95.
2. Pull pricing from each provider's docs as of run date.
3. Score each provider 0–10 on each axis; weighted total drives the order in `provider_equivalence.py`.

Done when: `docs/AGGREGATOR_RANKING.md` exists with the table, refreshed monthly.

### Phase 5 — Wiring plan — direct first, ranked aggregators next, redundant backups last

This is the change to the actual hot path. **No regressions, no quality changes** — we are only changing *which provider serves the call*, not orchestration logic, prompts, sampling, or post-processing.

Implementation:
1. **Stop hard-routing to OpenRouter.** Replace the `if openrouter_available: provider = "openrouter"` branch in `orchestrator.py` and `EliteOrchestrator._build_model_provider_map` with a lookup against a new `select_primary_provider(model_id)` helper.
2. The helper consults a per-model preference list:
   - **Direct first** if a first-party client + key is healthy (OpenAI for GPT, Anthropic for Claude, Google AI Studio for Gemini, xAI for Grok, DeepSeek for DeepSeek, Mistral for Mistral, etc.).
   - **Aggregators next** in ranked order from Phase 4. OpenRouter stays in the list — it just isn't always first anymore.
   - **Backups last** (DeepInfra / HuggingFace / Replicate) for spillover.
3. Per-model overrides live in an expanded `SAME_MODEL_PROVIDER_MATRIX`. For every `:free` slug, ensure the list has at least 2 providers (e.g. `deepseek/deepseek-chat:free` → `[openrouter, deepseek_direct, together, fireworks]`).
4. Failover semantics stay identical to today: a non-2xx, a 429, or a content-policy block triggers the next provider in the list. Per-provider circuit breaker already in `provider_router.py` keeps tripped providers cool for 60s.
5. Behind a feature flag: `ROUTING_V2_ENABLED=true` — default `false` initially. Roll out by user-id buckets (10% → 50% → 100%) over a week, watch error rate and p95 latency dashboards.

Done when:
- Flag at 100% on prod for 7 days with error rate ≤ baseline and p95 latency ≤ baseline + 50ms.
- Synthetic traffic test shows that simulated OpenRouter 429 storms now succeed via fallback in ≥99% of cases.

---

## 3. Concrete file/code touchpoints

| Area | File | What changes |
|---|---|---|
| Verify script (new) | `scripts/verify_direct_providers.py` | Phase 1+2+3 ping/load |
| Routing primary | `llmhive/src/llmhive/app/orchestrator.py` (≈line 2702-2730) | Replace hard OpenRouter selection with helper |
| Elite routing | `llmhive/src/llmhive/app/orchestration/elite_orchestration.py` (≈1238-1242) | Same helper |
| Same-model matrix | `llmhive/src/llmhive/app/intelligence/provider_equivalence.py` | Expand entries; cover free slugs |
| New clients | `llmhive/src/llmhive/app/providers/fireworks_client.py` (new) | HTTP client |
| New clients | `llmhive/src/llmhive/app/providers/deepinfra_client.py` (new) | HTTP client |
| New clients | `llmhive/src/llmhive/app/providers/replicate_client.py` (new) | HTTP client |
| Provider router | `llmhive/src/llmhive/app/providers/provider_router.py` | Register new clients, extend `try_all_fallbacks` |
| Feature flag | `llmhive/src/llmhive/app/config.py` | `ROUTING_V2_ENABLED` |
| Docs | `docs/PROVIDER_BILLING_STATUS.md`, `docs/AGGREGATOR_RANKING.md` | Phase 1, Phase 4 outputs |

---

## 4. Status checklist (update as we go)

- [ ] Phase 1 — direct provider verify script + billing audit
- [ ] Phase 2 — aggregator verify + billing audit
- [ ] Phase 3 — Fireworks + DeepInfra + Replicate wired (Vertex skipped)
- [ ] Phase 4 — ranking table published
- [ ] Phase 5a — `select_primary_provider` helper + flag (default off)
- [ ] Phase 5b — `SAME_MODEL_PROVIDER_MATRIX` expanded for all free slugs
- [ ] Phase 5c — synthetic chaos test passes
- [ ] Phase 5d — flag at 100% for 7 days, dashboards green

---

## 5. Hard rules (do not violate)

1. **No quality regression.** Orchestration logic, prompts, sampling, judges, verifiers stay untouched.
2. **No silent provider switch.** Every route decision is logged with `model_id`, `chosen_provider`, `reason`, `attempt_index`.
3. **No Vertex without an explicit, separate decision.** AI Studio + a second key is the Gemini redundancy plan.
4. **Spend guard stays the source of truth on cost limits.** New providers must integrate with the existing `SpendGuard` before going live.
5. **Feature-flagged rollout.** No hot-path change ships at 100% on day one.
