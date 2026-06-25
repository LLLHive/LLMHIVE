#!/usr/bin/env node
/**
 * OpenRouter guardrails + production key alignment for LLMHive.
 *
 * Uses OpenRouter **Management API** keys (not inference keys).
 * Create one at: https://openrouter.ai/settings/management-keys
 *
 * Usage:
 *   OPENROUTER_MANAGEMENT_API_KEY=sk-or-mgmt-... node scripts/openrouter-guardrails.mjs status
 *   OPENROUTER_MANAGEMENT_API_KEY=sk-or-mgmt-... node scripts/openrouter-guardrails.mjs plan
 *   OPENROUTER_MANAGEMENT_API_KEY=sk-or-mgmt-... node scripts/openrouter-guardrails.mjs apply
 *
 * Optional:
 *   OPENROUTER_GUARDRAIL_MONTHLY_USD=900  (override monthly limit)
 */
import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..")
const envLocal = path.join(root, ".env.local")

function parseDotenv(text) {
  const out = {}
  for (const line of text.split("\n")) {
    const t = line.trim()
    if (!t || t.startsWith("#")) continue
    const eq = t.indexOf("=")
    if (eq === -1) continue
    const key = t.slice(0, eq).trim()
    let val = t.slice(eq + 1).trim()
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1)
    }
    out[key] = val
  }
  return out
}

const fileEnv = fs.existsSync(envLocal) ? parseDotenv(fs.readFileSync(envLocal, "utf8")) : {}
const env = { ...fileEnv, ...process.env }

const MGMT_KEY = (env.OPENROUTER_MANAGEMENT_API_KEY || env.OPENROUTER_MGMT_API_KEY || "").trim()
const BASE = "https://openrouter.ai/api/v1"

function readJson(rel) {
  return JSON.parse(fs.readFileSync(path.join(root, rel), "utf8"))
}

function uniqueSorted(values) {
  return [...new Set(values.filter(Boolean))].sort()
}

function collectAllowedModels() {
  const spec = readJson("data/billing/openrouter_production_guardrail.json")
  const roster = readJson(spec.model_allowlist_source)
  const fromUi = (roster.ui_models || []).map((m) => m.model_id)
  const fromPaid = (roster.paid_catalog || []).map((m) => m.model_id)
  const extra = spec.extra_allowed_models || []
  return uniqueSorted([...fromUi, ...fromPaid, ...extra])
}

function buildGuardrailPayload(spec) {
  const monthly = Number(env.OPENROUTER_GUARDRAIL_MONTHLY_USD || spec.limit_usd || 900)
  return {
    name: spec.name,
    description: spec.description,
    limit_usd: monthly,
    reset_interval: spec.reset_interval || "monthly",
    allowed_models: collectAllowedModels(),
    enforce_zdr_openai: spec.enforce_zdr_openai ?? true,
    enforce_zdr_anthropic: spec.enforce_zdr_anthropic ?? true,
    enforce_zdr_google: spec.enforce_zdr_google ?? true,
    enforce_zdr_other: spec.enforce_zdr_other ?? false,
    content_filter_builtins: spec.content_filter_builtins || [],
  }
}

async function orFetch(method, pathname, body) {
  const res = await fetch(`${BASE}${pathname}`, {
    method,
    headers: {
      Authorization: `Bearer ${MGMT_KEY}`,
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: body ? JSON.stringify(body) : undefined,
  })
  const text = await res.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  if (!res.ok) {
    const msg = typeof data === "object" ? JSON.stringify(data) : String(data)
    const err = new Error(`${method} ${pathname} failed (${res.status}): ${msg}`)
    err.status = res.status
    throw err
  }
  return data
}

function requireMgmtKey() {
  if (!MGMT_KEY) {
    console.error(
      "OPENROUTER_MANAGEMENT_API_KEY is required.\n" +
        "Create a Management key at https://openrouter.ai/settings/management-keys\n" +
        "(Inference keys like open-router-key cannot manage guardrails.)",
    )
    process.exit(1)
  }
}

async function listKeys() {
  const data = await orFetch("GET", "/keys")
  return data?.data || data || []
}

async function listGuardrails() {
  const data = await orFetch("GET", "/guardrails")
  return data?.data || data || []
}

function printKeyRow(key) {
  const name = key.name || key.label || "(unnamed)"
  const hash = key.hash || key.id || "?"
  const limit = key.limit != null ? `$${key.limit}` : "unlimited"
  const usage = key.usage != null ? `$${Number(key.usage).toFixed(2)}` : "?"
  const remaining =
    key.limit_remaining != null ? `$${Number(key.limit_remaining).toFixed(2)}` : "?"
  const guardrails = key.guardrail?.name || key.guardrail_name || "No guardrails"
  console.log(`  • ${name}`)
  console.log(`      hash: ${hash}`)
  console.log(`      usage: ${usage} / ${limit} (remaining ${remaining})`)
  console.log(`      guardrails: ${guardrails}`)
}

async function cmdStatus() {
  requireMgmtKey()
  const spec = readJson("data/billing/openrouter_production_guardrail.json")
  const caps = readJson("data/billing/tier_cost_caps.json")

  console.log("=== OpenRouter keys ===")
  const keys = await listKeys()
  for (const key of keys) printKeyRow(key)

  console.log("\n=== Guardrails ===")
  const guardrails = await listGuardrails()
  if (!guardrails.length) {
    console.log("  (none)")
  } else {
    for (const g of guardrails) {
      console.log(`  • ${g.name} (${g.id})`)
      console.log(`      limit: $${g.limit_usd ?? "?"} / ${g.reset_interval || "?"}`)
      console.log(
        `      models: ${g.allowed_models?.length ? g.allowed_models.length + " allowed" : "all"}`,
      )
    }
  }

  const target = keys.find((k) => (k.name || "") === spec.target_key_name)
  console.log("\n=== LLMHive alignment ===")
  console.log(`  Target key: ${spec.target_key_name} ${target ? "✓ found" : "✗ NOT FOUND"}`)
  console.log(`  Per-request caps (app): ${JSON.stringify(caps.per_request_max_cost_usd)}`)
  console.log(`  Proposed guardrail monthly: $${env.OPENROUTER_GUARDRAIL_MONTHLY_USD || spec.limit_usd}`)
  console.log(`  Proposed model allowlist: ${collectAllowedModels().length} models`)
}

async function cmdPlan() {
  requireMgmtKey()
  const spec = readJson("data/billing/openrouter_production_guardrail.json")
  const payload = buildGuardrailPayload(spec)
  const keys = await listKeys()
  const target = keys.find((k) => (k.name || "") === spec.target_key_name)
  if (!target) {
    console.error(`Key "${spec.target_key_name}" not found in workspace.`)
    process.exit(1)
  }

  console.log("Dry run — would upsert guardrail:")
  console.log(JSON.stringify(payload, null, 2))
  console.log(`\nWould assign to key hash: ${target.hash || target.id}`)
  console.log(`Model allowlist count: ${payload.allowed_models.length}`)
}

async function cmdApply() {
  requireMgmtKey()
  const spec = readJson("data/billing/openrouter_production_guardrail.json")
  const payload = buildGuardrailPayload(spec)
  const keys = await listKeys()
  const target = keys.find((k) => (k.name || "") === spec.target_key_name)
  if (!target) {
    console.error(`Key "${spec.target_key_name}" not found.`)
    process.exit(1)
  }
  const keyHash = target.hash || target.id

  const existing = (await listGuardrails()).find((g) => g.name === spec.name)
  let guardrailId
  if (existing?.id) {
    console.log(`Updating guardrail ${spec.name} (${existing.id})...`)
    const updated = await orFetch("PATCH", `/guardrails/${existing.id}`, payload)
    guardrailId = updated?.data?.id || updated?.id || existing.id
  } else {
    console.log(`Creating guardrail ${spec.name}...`)
    const created = await orFetch("POST", "/guardrails", payload)
    guardrailId = created?.data?.id || created?.id
  }

  if (!guardrailId) {
    console.error("Could not resolve guardrail id after create/update.")
    process.exit(1)
  }

  console.log(`Assigning to key ${spec.target_key_name} (${keyHash})...`)
  const assign = await orFetch("POST", `/guardrails/${guardrailId}/assignments/keys`, {
    key_hashes: [keyHash],
  })
  console.log("Done.")
  console.log(JSON.stringify({ guardrail_id: guardrailId, assignment: assign }, null, 2))
}

const cmd = (process.argv[2] || "status").toLowerCase()
try {
  if (cmd === "status") await cmdStatus()
  else if (cmd === "plan") await cmdPlan()
  else if (cmd === "apply") await cmdApply()
  else {
    console.error("Usage: node scripts/openrouter-guardrails.mjs [status|plan|apply]")
    process.exit(1)
  }
} catch (err) {
  if (err.status === 403 || err.status === 401) {
    console.error(
      "\nAuth failed — use a Management API key, not the inference open-router-key.",
    )
  }
  console.error(err.message || err)
  process.exit(1)
}
