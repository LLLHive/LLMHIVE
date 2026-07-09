"use client"

import { useEffect } from "react"
import { usePathname, useSearchParams } from "next/navigation"

import {
  GA_MEASUREMENT_ID,
  isGoogleAnalyticsEnabled,
} from "@/lib/marketing/google-analytics"

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void
  }
}

/** Fire GA4 page_view on App Router client navigations (initial load handled by gtag config). */
export function GoogleAnalyticsPageview() {
  const pathname = usePathname()
  const searchParams = useSearchParams()

  useEffect(() => {
    if (!isGoogleAnalyticsEnabled()) return
    if (!pathname || typeof window.gtag !== "function") return

    const query = searchParams?.toString()
    const pagePath = query ? `${pathname}?${query}` : pathname

    window.gtag("config", GA_MEASUREMENT_ID, {
      page_path: pagePath,
    })
  }, [pathname, searchParams])

  return null
}
