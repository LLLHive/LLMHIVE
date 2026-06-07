"use client"

import { usePathname } from "next/navigation"
import { MarketingNav } from "@/components/marketing/MarketingNav"

/** Pages that ship their own sticky header — skip the shared MarketingNav. */
const STANDALONE_MARKETING_PATHS = ["/landing", "/promo", "/demo"] as const

function isStandaloneMarketingPath(pathname: string): boolean {
  return STANDALONE_MARKETING_PATHS.some(
    (base) => pathname === base || pathname.startsWith(`${base}/`),
  )
}

export function MarketingLayoutChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? ""
  const standalone = isStandaloneMarketingPath(pathname)

  return (
    <>
      {!standalone ? (
        <>
          <MarketingNav />
          <div className="h-16" aria-hidden />
        </>
      ) : null}
      {children}
    </>
  )
}
