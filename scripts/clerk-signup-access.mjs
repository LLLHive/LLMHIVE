#!/usr/bin/env node
/**
 * Clerk sign-up access diagnostics and fixes.
 *
 * Error seen by users:
 *   "<email> is not allowed to access this application."
 *
 * Root cause: Clerk allowlist (or restricted sign-up) enabled — only listed
 * emails/phones can register.
 *
 * Usage:
 *   node scripts/clerk-signup-access.mjs status
 *   node scripts/clerk-signup-access.mjs disable-allowlist
 *   node scripts/clerk-signup-access.mjs add-email user@example.com
 *   node scripts/clerk-signup-access.mjs add-phone +13322568356
 *
 * Requires CLERK_SECRET_KEY (sk_live_… for production).
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
const secret = (env.CLERK_SECRET_KEY || "").trim()

if (!secret) {
  console.error("CLERK_SECRET_KEY is required (set in .env.local or environment).")
  process.exit(1)
}

const API = "https://api.clerk.com/v1"

async function clerk(pathname, { method = "GET", body } = {}) {
  const res = await fetch(`${API}${pathname}`, {
    method,
    headers: {
      Authorization: `Bearer ${secret}`,
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
    throw new Error(`${method} ${pathname} failed (${res.status}): ${msg}`)
  }
  return data
}

async function status() {
  const [instance, allowlist, blocklist] = await Promise.all([
    clerk("/instance"),
    clerk("/allowlist_identifiers?limit=100"),
    clerk("/blocklist_identifiers?limit=100"),
  ])

  const allowItems = Array.isArray(allowlist) ? allowlist : allowlist?.data || []
  const blockItems = blocklist?.data || []

  console.log("--- Clerk sign-up access ---")
  console.log("Instance:", instance?.id, `(${instance?.environment_type || "unknown"})`)
  console.log(
    "Tip: Clerk has no read-only restrictions API. If sign-ups fail with",
  )
  console.log(
    '"not allowed to access this application", run: disable-allowlist',
  )

  console.log(`\nAllowlist entries (used only when allowlist mode is ON): ${allowItems.length}`)
  for (const row of allowItems) {
    console.log(`  - ${row.identifier}`)
  }
  console.log(`Blocklist entries: ${blockItems.length}`)
  for (const row of blockItems) {
    console.log(`  - ${row.identifier}`)
  }
}

async function disableAllowlist() {
  const res = await clerk("/instance/restrictions", {
    method: "PATCH",
    body: { allowlist: false },
  })
  console.log("Updated restrictions:", res)
  console.log("Allowlist disabled — new users can sign up with any email/phone.")
}

async function addIdentifier(identifier) {
  const res = await clerk("/allowlist_identifiers", {
    method: "POST",
    body: { identifier, notify: false },
  })
  console.log("Added to allowlist:", res.identifier || res)
}

const [cmd, arg] = process.argv.slice(2)

try {
  if (cmd === "status") {
    await status()
  } else if (cmd === "disable-allowlist") {
    await disableAllowlist()
  } else if (cmd === "add-email" && arg) {
    await addIdentifier(arg.trim().toLowerCase())
  } else if (cmd === "add-phone" && arg) {
    await addIdentifier(arg.trim())
  } else {
    console.log(`Usage:
  node scripts/clerk-signup-access.mjs status
  node scripts/clerk-signup-access.mjs disable-allowlist
  node scripts/clerk-signup-access.mjs add-email user@example.com
  node scripts/clerk-signup-access.mjs add-phone +15551234567`)
    process.exit(cmd ? 1 : 0)
  }
} catch (err) {
  console.error(err.message || err)
  process.exit(1)
}
