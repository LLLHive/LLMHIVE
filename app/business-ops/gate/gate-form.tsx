"use client"

import { useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

export function BusinessOpsGateForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const returnTo = searchParams.get("returnTo") || "/business-ops"
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      const res = await fetch("/api/business-ops/unlock", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
        credentials: "include",
      })
      const data = (await res.json().catch(() => ({}))) as { error?: string }
      if (!res.ok) {
        setError(typeof data.error === "string" ? data.error : "Could not verify password")
        return
      }
      router.push(returnTo.startsWith("/") ? returnTo : "/business-ops")
      router.refresh()
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md space-y-6 border border-border rounded-xl p-8 bg-card">
        <h1 className="text-xl font-semibold">Business Ops access</h1>
        <p className="text-sm text-muted-foreground">
          This area is for the management team only. Use your LLMHive account, then enter the operations password you were given.
        </p>
        <form onSubmit={onSubmit} className="space-y-4">
          <Input
            type="password"
            name="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Operations password"
            disabled={loading}
          />
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Checking…" : "Continue"}
          </Button>
        </form>
        <p className="text-xs text-muted-foreground text-center">
          <Link href="/" className="underline">
            Back to app
          </Link>
        </p>
      </div>
    </div>
  )
}
