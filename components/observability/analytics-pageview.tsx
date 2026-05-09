"use client"

import { useEffect, useRef } from "react"
import { usePathname, useSearchParams } from "next/navigation"
import { useUser } from "@clerk/nextjs"

import {
  identify,
  isAnalyticsConfigured,
  pageview,
} from "@/lib/observability/analytics"

/**
 * Auto-tracks `$pageview` on every route change and `identify`s the Clerk
 * user once per session so PostHog can associate subsequent events with the
 * authenticated account. No-op when `NEXT_PUBLIC_POSTHOG_KEY` is unset.
 *
 * Mount once near the root of the app (already done in app/layout.tsx).
 */
export function AnalyticsPageview() {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const { isLoaded, isSignedIn, user } = useUser()
  const identifiedRef = useRef<string | null>(null)

  // Pageview on every route change.
  useEffect(() => {
    if (!isAnalyticsConfigured()) return
    if (!pathname) return
    const query = searchParams?.toString()
    const fullPath = query ? `${pathname}?${query}` : pathname
    void pageview(fullPath)
  }, [pathname, searchParams])

  // Identify the user once Clerk resolves a signed-in session.
  useEffect(() => {
    if (!isAnalyticsConfigured()) return
    if (!isLoaded || !isSignedIn || !user?.id) return
    if (identifiedRef.current === user.id) return
    identifiedRef.current = user.id
    void identify(user.id, {
      email: user.primaryEmailAddress?.emailAddress,
      created_at: user.createdAt?.toISOString?.() ?? null,
    })
  }, [isLoaded, isSignedIn, user?.id, user?.primaryEmailAddress?.emailAddress, user?.createdAt])

  return null
}
