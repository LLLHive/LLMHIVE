"use client"

import { Analytics } from "@vercel/analytics/react"

export function AnalyticsWrapper() {
  // Only render in production
  if (process.env.NODE_ENV !== "production") {
    return null
  }

  return <Analytics />
}
