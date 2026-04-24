#!/usr/bin/env node
/**
 * Safe Clerk env diagnostics (no secret values printed).
 * Run: node scripts/verify-clerk-env.mjs
 * Loads .env.local from repo root when present, then merges process.env.
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

const pk = (env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || "").trim()
const sk = (env.CLERK_SECRET_KEY || "").trim()

function diagnose(name, value) {
  if (!value) return { present: false, len: 0, prefix: "", note: "missing" }
  const prefix = value.slice(0, 8)
  return { present: true, len: value.length, prefix, note: "" }
}

const dPk = diagnose("pk", pk)
const dSk = diagnose("sk", sk)

console.log("--- Clerk env (sanitized) ---")
console.log("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY:", dPk)
console.log("CLERK_SECRET_KEY:", dSk)
console.log("")

if (pk.startsWith("sk_test_") || pk.startsWith("sk_live_")) {
  console.error(
    "ERROR: NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY starts with sk_ — that is the SECRET key.\n" +
      "Use the Publishable key (pk_test_… / pk_live_…) from Clerk → API Keys."
  )
  process.exitCode = 1
} else if (pk && !pk.startsWith("pk_test_") && !pk.startsWith("pk_live_")) {
  console.error("ERROR: Publishable key must start with pk_test_ or pk_live_.")
  process.exitCode = 1
} else if (pk && pk.length < 20) {
  console.warn(
    `WARNING: Publishable key is only ${pk.length} characters — likely truncated or a placeholder.\n` +
      "Re-copy from Clerk → API Keys (Publishable key, pk_test_… / pk_live_…)."
  )
}

if (sk && !sk.startsWith("sk_test_") && !sk.startsWith("sk_live_")) {
  console.warn("WARNING: CLERK_SECRET_KEY should normally start with sk_test_ or sk_live_.")
}

console.log("Done.")
