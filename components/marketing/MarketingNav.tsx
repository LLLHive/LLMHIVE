import Image from "next/image"
import Link from "next/link"
import { auth } from "@clerk/nextjs/server"
import LogoText from "@/components/branding/LogoText"
import { MarketingNavAuthButtons } from "@/components/marketing/MarketingNavAuthButtons"

/**
 * Shared marketing-site header.
 *
 * Renders on every public page (`/`, `/pricing`, `/about`, all of
 * `app/(marketing)/*`). The top-right shows auth controls only — no
 * "Choose your plan" / "Open app" CTA there. Plan-selection lives in the
 * hero, the pricing teaser, and the dedicated `/pricing` page; this nav
 * only handles "are you logged in or not".
 *
 *  - Anonymous:  Sign Up (-> /pricing)  + Sign In (-> /sign-in)
 *  - Signed-in:  Sign Out (returns to /)
 *
 * Signed-in users never see "Sign In" — that link would force-redirect
 * through Clerk and bounce off the /app entitlement gate to /pricing.
 */
export async function MarketingNav() {
  const { userId } = await auth()
  const isSignedIn = Boolean(userId)

  return (
    <nav className="fixed inset-x-0 top-0 z-50 border-b border-white/5 bg-black/60 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2.5">
          <Image src="/logo.png" alt="LLMHive" width={32} height={32} priority className="h-8 w-8" />
          {/* Same wordmark asset the rest of the site uses (LogoText →
              /llmhive/llmhive-wordmark-nav.png), so the corner brand
              matches /app exactly instead of pulling a different file
              from /brand/. */}
          <LogoText height={26} variant="nav" className="hidden sm:block" />
        </Link>

        <div className="hidden items-center gap-7 md:flex">
          <Link href="/#features" className="text-sm text-zinc-400 transition-colors hover:text-white">
            Features
          </Link>
          <Link href="/#how-it-works" className="text-sm text-zinc-400 transition-colors hover:text-white">
            How it works
          </Link>
          <Link href="/pricing" className="text-sm text-zinc-400 transition-colors hover:text-white">
            Pricing
          </Link>
          <Link href="/about" className="text-sm text-zinc-400 transition-colors hover:text-white">
            About
          </Link>
          <Link href="/contact" className="text-sm text-zinc-400 transition-colors hover:text-white">
            Contact
          </Link>
        </div>

        <div className="flex items-center gap-2 sm:gap-3">
          <MarketingNavAuthButtons isSignedIn={isSignedIn} />
        </div>
      </div>
    </nav>
  )
}
