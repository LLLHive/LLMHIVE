# Launch Command Sheet

Date: `2026-04-05`

## Launch Basis

Use this exact frozen basis for launch:

- Frontend production deployment: `dpl_5xM7JRURbxAZEYrv4G5cLC2pQqge`
- Frontend alias: `https://www.llmhive.ai`
- Backend serving revision: `llmhive-orchestrator-02203-grk`
- Free benchmark basis: `benchmark_reports/category_benchmarks_free_20260331.json`
- Elite benchmark basis: `benchmark_reports/category_benchmarks_elite_20260401.json`

Do not make more runtime changes before launch.

## Launch Window

- Planned launch date: `________________`
- Planned launch time: `________________`
- Launch timezone: `________________`

## Owner Assignments

- Support owner: `________________`
- Backup support owner: `________________`
- Production monitoring owner: `________________`
- Backup monitoring owner: `________________`
- Go / no-go approver: `________________`
- Rollback executor: `________________`
- Benchmark source-of-truth owner: `________________`
- Pricing/package owner: `________________`

## Contact Methods

- Support channel: `________________`
- Monitoring channel: `________________`
- Launch war-room / chat: `________________`
- Escalation phone / backup contact: `________________`

## Frozen Public Pricing

Use the live pricing basis only:

- Free: `$0`
- Lite: `$14.99/month`
- Pro: `$29.99/month`
- Enterprise: `$35/seat/month`
- Enterprise minimum: `5 seats ($175+/month)`

## Frozen Benchmark Claim Basis

Use the same benchmark basis everywhere:

- Free:
  - Overall: `93.3%`
  - Reasoning: `85.1%`
  - Coding: `96.0%`
  - Math: `100.0%`
  - Multilingual: `87.0%`
  - Long Context: `100.0%`
  - Tool Use: `100.0%`
  - RAG: `49.7%`
  - Dialogue: `7.5 / 10`

- Elite:
  - Overall: `93.5%`
  - Reasoning: `88.8%`
  - Coding: `100.0%`
  - Math: `97.9%`
  - Multilingual: `88.4%`
  - Long Context: `100.0%`
  - Tool Use: `100.0%`
  - RAG: `55.4%`
  - Dialogue: `7.2 / 10`

Rules:

- do not mix benchmark dates
- do not regenerate launch tables
- do not overclaim disputed zero-cost Elite telemetry

## Pre-Launch Go / No-Go

Mark each one `YES` before launch:

- [ ] `YES` Frontend homepage `/` is public marketing
- [ ] `YES` `/workspace` is the authenticated app entry
- [ ] `YES` `/press`, `/faq`, `/help`, `/case-studies`, and `/comparisons/llmhive-vs-chatgpt` render publicly
- [ ] `YES` `/sign-in` loads correctly
- [ ] `YES` `/llms.txt` returns `200`
- [ ] `YES` `/api/health/integrations` returns `200`
- [ ] `YES` Backend traffic is still `100% -> llmhive-orchestrator-02203-grk`
- [ ] `YES` Benchmark tables are frozen to the approved basis
- [ ] `YES` Pricing/package wording is frozen to the live basis
- [ ] `YES` Support owner is assigned
- [ ] `YES` Monitoring owner is assigned
- [ ] `YES` Go / no-go approver is assigned
- [ ] `YES` No more runtime changes are queued

If any box cannot be checked, do not launch yet.

## Launch Sequence

1. Reconfirm frontend alias and homepage.
2. Reconfirm backend serving revision.
3. Reconfirm no unauthorized production automation is active.
4. Reconfirm support and monitoring owners are online.
5. Publish launch materials.
6. Watch support and monitoring channels actively.

## What To Watch During Launch

### Support owner watches

- contact form traffic
- support inbox
- billing complaints
- sign-in complaints
- customer confusion about plans/pricing

### Monitoring owner watches

- backend health
- `/v1/chat` latency
- frontend availability
- auth/sign-in failures
- production error spikes

## Rollback Triggers

Rollback should be considered if any of these happen:

- homepage or key public routes stop loading publicly
- sign-in flow is broken for real users
- backend `/health` fails
- backend `/v1/chat` shows sustained failure
- production error rate spikes materially
- support reports repeated critical billing or auth failures

## Rollback References

- Frontend live deployment: `dpl_5xM7JRURbxAZEYrv4G5cLC2pQqge`
- Backend serving revision: `llmhive-orchestrator-02203-grk`
- Launch packet: `artifacts/launch_freeze/launch_source_of_truth_packet_20260405.md`
- Final checklist: `artifacts/launch_freeze/final_launch_readiness_checklist_20260405.md`

## Final Decision

- Go / no-go decision: `________________`
- Approved by: `________________`
- Approval time: `________________`

## Rule For Tonight

No more product changes.

Only launch operations, monitoring, and rollback if needed.
