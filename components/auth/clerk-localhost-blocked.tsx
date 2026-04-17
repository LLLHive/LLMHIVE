import Link from "next/link"
import { Button } from "@/components/ui/button"
import { AlertCircle, ExternalLink } from "lucide-react"

/** Shown on /sign-in and /sign-up when pk_live_ is used on localhost (Clerk blocks the embedded UI). */
export function ClerkLocalhostBlockedMessage({ mode }: { mode: "sign-in" | "sign-up" }) {
  const prodUrl = mode === "sign-in" ? "https://www.llmhive.ai/sign-in" : "https://www.llmhive.ai/sign-up"
  const headline = mode === "sign-in" ? "Sign in to LLMHive" : "Create your LLMHive account"

  return (
    <div
      className={[
        "w-full max-w-[400px] rounded-xl border border-white/10",
        "bg-background/85 backdrop-blur-xl shadow-2xl",
        "text-left text-foreground",
      ].join(" ")}
    >
      {/* Match production Clerk card header rhythm */}
      <div className="border-b border-white/10 px-6 pt-6 pb-4">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-amber-500/15 text-amber-400 ring-1 ring-amber-500/25">
            <AlertCircle className="h-5 w-5" aria-hidden />
          </div>
          <div className="min-w-0 space-y-1">
            <p className="text-xs font-medium uppercase tracking-wide text-zinc-400">Local development</p>
            <h2 className="text-lg font-semibold leading-snug text-white">{headline}</h2>
            <p className="text-sm leading-relaxed text-zinc-300">
              The dev server is using Clerk <span className="font-medium text-white">production</span> keys (
              <code className="rounded bg-black/50 px-1.5 py-0.5 text-xs text-zinc-200">pk_live_</code>
              ). Clerk only accepts those on <span className="font-medium text-white">llmhive.ai</span>, so the
              sign-in form cannot load on localhost.
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-4 px-6 py-5">
        <p className="text-sm font-medium text-white">Use development keys</p>
        <ol className="list-decimal space-y-2 pl-5 text-sm leading-relaxed text-zinc-300">
          <li>
            Clerk Dashboard → ensure <strong className="text-zinc-100">Development</strong> is selected
          </li>
          <li>
            Copy <code className="mx-0.5 rounded bg-black/50 px-1.5 py-0.5 text-xs text-emerald-300/90">pk_test_</code>{" "}
            and <code className="mx-0.5 rounded bg-black/50 px-1.5 py-0.5 text-xs text-emerald-300/90">sk_test_</code>{" "}
            into <code className="rounded bg-black/50 px-1.5 py-0.5 text-xs text-zinc-200">.env.local</code>
          </li>
          <li>
            Restart <code className="rounded bg-black/50 px-1.5 py-0.5 text-xs text-zinc-200">npm run dev</code> — the
            normal sign-in UI will match production.
          </li>
        </ol>

        <div className="h-px bg-white/10" />

        <p className="text-center text-xs text-zinc-500">or continue on production</p>

        <Button
          asChild
          className="w-full gap-2 bronze-gradient text-base font-medium shadow-lg"
          size="lg"
        >
          <Link href={prodUrl} target="_blank" rel="noopener noreferrer">
            {mode === "sign-in" ? "Open sign-in on llmhive.ai" : "Open sign-up on llmhive.ai"}
            <ExternalLink className="h-4 w-4 opacity-90" />
          </Link>
        </Button>
      </div>
    </div>
  )
}
