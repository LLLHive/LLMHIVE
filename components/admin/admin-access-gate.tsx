"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Copy, Check, Shield, LogIn } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"

interface MeResponse {
  signedIn: boolean
  userId?: string
  isAdmin?: boolean
  adminConfigured?: boolean
  hint?: string
}

export function AdminAccessGate({ message }: { message?: string }) {
  const [me, setMe] = useState<MeResponse | null>(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    fetch("/api/admin/me")
      .then((r) => r.json())
      .then(setMe)
      .catch(() => setMe({ signedIn: false }))
  }, [])

  const copyUserId = async () => {
    if (!me?.userId) return
    await navigator.clipboard.writeText(me.userId)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Card className="max-w-lg mx-auto mt-16 border-border/50 bg-card/80 backdrop-blur-sm">
      <CardContent className="pt-8 pb-8 space-y-6">
        <div className="flex flex-col items-center gap-3 text-center">
          <Shield className="h-12 w-12 text-[var(--bronze)]" />
          <h2 className="text-xl font-bold">{message ?? "Admin access required"}</h2>
        </div>

        {!me && <p className="text-sm text-muted-foreground text-center">Checking session…</p>}

        {me && !me.signedIn && (
          <div className="space-y-4 text-center">
            <p className="text-sm text-muted-foreground">
              Sign in with your LLMHive account first, then return to the admin console.
            </p>
            <Button asChild className="w-full">
              <Link href="/sign-in?redirect_url=/admin/dashboard">
                <LogIn className="h-4 w-4 mr-2" />
                Sign in
              </Link>
            </Button>
          </div>
        )}

        {me?.signedIn && !me.isAdmin && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground text-center">
              Your account is signed in but not in the admin allowlist.
            </p>
            <div className="rounded-lg border border-border/50 bg-muted/30 p-4 space-y-3">
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Your Clerk user ID
              </p>
              <div className="flex items-center gap-2">
                <code className="flex-1 text-xs font-mono bg-background px-3 py-2 rounded border truncate">
                  {me.userId}
                </code>
                <Button variant="outline" size="icon" onClick={copyUserId} aria-label="Copy user ID">
                  {copied ? <Check className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                Add to <code className="text-foreground">.env.local</code>:
              </p>
              <pre className="text-xs font-mono bg-background px-3 py-2 rounded border overflow-x-auto">
                ADMIN_USER_IDS={me.userId}
              </pre>
              <p className="text-xs text-amber-500/90">
                Restart <code>npm run dev</code> after saving, then reload this page.
              </p>
            </div>
          </div>
        )}

        {me?.signedIn && me.isAdmin && (
          <div className="text-center space-y-3">
            <p className="text-sm text-emerald-500">You have admin access.</p>
            <Button asChild>
              <Link href="/admin/dashboard">Open Command Center</Link>
            </Button>
          </div>
        )}

        <Button variant="ghost" asChild className="w-full">
          <Link href="/">Return to Home</Link>
        </Button>
      </CardContent>
    </Card>
  )
}
