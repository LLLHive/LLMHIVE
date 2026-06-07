"use client"

import { usePathname } from "next/navigation"

/** Pages that ship their own sticky header — skip the shared MarketingNav. */
const STANDALONE_MARKETING_PATHS = ["/landing", "/promo", "/demo"] as const

function isStandaloneMarketingPath(pathname: string): boolean {
  return STANDALONE_MARKETING_PATHS.some(
    (base) => pathname === base || pathname.startsWith(`${base}/`),
  )
}

type Props = {
  children: React.ReactNode
  /** Server-rendered <MarketingNav /> passed from the marketing layout. */
  nav: React.ReactNode
}

export function MarketingLayoutChrome({ children, nav }: Props) {
  const pathname = usePathname() ?? ""
  const standalone = isStandaloneMarketingPath(pathname)

  return (
    <>
      {!standalone ? (
        <>
          {nav}
          <div className="h-16" aria-hidden />
        </>
      ) : null}
      {children}
    </>
  )
}
