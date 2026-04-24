#!/usr/bin/env node
/**
 * Verify OpenRouter model slugs referenced in static UI / fallbacks exist in the
 * live catalog (https://openrouter.ai/api/v1/models).
 *
 * - Exits 1 only when the API returns a model list AND at least one referenced ID is missing.
 * - Exits 0 when the API is unreachable (network/5xx) so CI is not blocked by third-party outages.
 *
 * Usage: node scripts/verify-openrouter-catalog-ids.mjs
 * Optional: OPENROUTER_VERIFY_STRICT=1 → exit 1 if the catalog cannot be fetched.
 */

import fs from "node:fs"
import path from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const ROOT = path.resolve(__dirname, "..")

const OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
const PROVIDER_PREFIX =
  "(?:openai|anthropic|google|deepseek|x-ai|meta-llama|qwen|mistralai|cohere|ai21|nousresearch)"

const FILES = [
  path.join(ROOT, "lib", "models.ts"),
  path.join(ROOT, "lib", "openrouter", "orchestrator-integration.ts"),
  path.join(ROOT, "app", "api", "openrouter", "category-rankings", "route.ts"),
  path.join(ROOT, "llmhive", "src", "llmhive", "app", "openrouter", "model_slug_remap.py"),
]

function collectIdsFromText(filePath, text) {
  const ids = new Set()
  const base = path.basename(filePath)

  if (base === "models.ts") {
    const re = new RegExp(`id:\\s*"(${PROVIDER_PREFIX}/[^"]+)"`, "g")
    let m
    while ((m = re.exec(text)) !== null) {
      ids.add(m[1])
    }
    return ids
  }

  if (base === "route.ts") {
    const re = new RegExp(`model_id:\\s*'(${PROVIDER_PREFIX}/[^']+)'`, "g")
    let m
    while ((m = re.exec(text)) !== null) {
      ids.add(m[1])
    }
    return ids
  }

  if (base === "orchestrator-integration.ts") {
    const re = new RegExp(`'(${PROVIDER_PREFIX}/[a-z0-9_.:-]+)'`, "gi")
    let m
    while ((m = re.exec(text)) !== null) {
      ids.add(m[1])
    }
    return ids
  }

  if (base === "model_slug_remap.py") {
    const re = new RegExp(
      `"(${PROVIDER_PREFIX}/[^"]+)"\\s*:\\s*"(${PROVIDER_PREFIX}/[^"]+)"`,
      "g",
    )
    let m
    while ((m = re.exec(text)) !== null) {
      ids.add(m[2])
    }
    return ids
  }

  return ids
}

function sleep(ms) {
  return new Promise((r) => setTimeout(r, ms))
}

async function fetchCatalog(attempts = 3) {
  let lastErr
  for (let i = 0; i < attempts; i++) {
    try {
      const res = await fetch(OPENROUTER_MODELS_URL, {
        headers: { Accept: "application/json" },
        signal: AbortSignal.timeout(45_000),
      })
      if (!res.ok) {
        lastErr = new Error(`HTTP ${res.status}`)
      } else {
        const json = await res.json()
        const rows = json.data
        if (!Array.isArray(rows)) {
          lastErr = new Error("Unexpected JSON: missing data[]")
        } else {
          return new Set(rows.map((r) => r.id).filter(Boolean))
        }
      }
    } catch (e) {
      lastErr = e
    }
    await sleep(1500 * (i + 1))
  }
  throw lastErr
}

function main() {
  const wanted = new Set()
  for (const fp of FILES) {
    if (!fs.existsSync(fp)) {
      console.error(`Missing file: ${path.relative(ROOT, fp)}`)
      process.exit(1)
    }
    const text = fs.readFileSync(fp, "utf8")
    for (const id of collectIdsFromText(fp, text)) {
      wanted.add(id)
    }
  }

  if (wanted.size === 0) {
    console.error("No model IDs collected — check extractors.")
    process.exit(1)
  }

  return fetchCatalog()
    .then((catalog) => {
      const missing = [...wanted].filter((id) => !catalog.has(id)).sort()
      if (missing.length) {
        console.error(
          `\nOpenRouter catalog check: ${missing.length} referenced ID(s) not found on ${OPENROUTER_MODELS_URL}:\n`,
        )
        for (const id of missing) console.error(`  - ${id}`)
        console.error(
          "\nFix slugs in lib/models.ts, category-rankings, orchestrator-integration, and/or model_slug_remap.py.\n",
        )
        process.exit(1)
      }
      console.log(
        `OpenRouter catalog OK — ${wanted.size} unique slug(s) verified across ${FILES.length} file(s).`,
      )
      process.exit(0)
    })
    .catch((err) => {
      const strict = process.env.OPENROUTER_VERIFY_STRICT === "1"
      console.warn(
        `\n[verify-openrouter-catalog-ids] Could not fetch OpenRouter catalog (${err?.message || err}).`,
      )
      console.warn(
        strict
          ? "OPENROUTER_VERIFY_STRICT=1 set — failing the job."
          : "Skipping failure (set OPENROUTER_VERIFY_STRICT=1 to fail on fetch errors).\n",
      )
      process.exit(strict ? 1 : 0)
    })
}

main()
