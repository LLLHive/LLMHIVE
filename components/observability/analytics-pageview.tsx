"use client"

import { useEffect } from "react"
import { usePathname, useSearchParams } from "next/navigation"

import { isAnalyticsConfigured, pageview } from "@/lib/observability/analytics"

/**
 * Fires a `$pageview` to PostHog on every route change when
 * `NEXT_PUBLIC_POSTHOG_KEY` is set. No-op otherwise — safe to mount
 * unconditionally.
 *
 * Mount once near the root of the app (e.g. inside `app/layout.tsx`).
 */
export function AnalyticsPageview() {
  const pathname = usePathname()
  const searchParams = useSearchParams()

  useEffect(() => {
    if (!isAnalyticsConfigured()) return
    if (!pathname) return
    const query = searchParams?.toString()
    const fullPath = query ? `${pathname}?${query}` : pathname
    void pageview(fullPath)
  }, [pathname, searchParams])

  return null
}
