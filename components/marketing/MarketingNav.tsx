import Image from "next/image"
import Link from "next/link"
import { auth } from "@clerk/nextjs/server"
import { SignOutButton } from "@clerk/nextjs"
import { LogIn, LogOut } from "lucide-react"
import { Button } from "@/components/ui/button"
import LogoText from "@/components/branding/LogoText"

/**
 * Shared marketing-site header.
 *
 * Renders on every public page (`/`, `/pricing`, `/about`, all of
 * `app/(marketing)/*`). The top-right shows auth controls only — no
 * "Choose your plan" / "Open app" CTA there. Plan-selection lives in the
 * hero, the pricing teaser, and the dedicated `/pricing` page; this nav
 * only handles "are you logged in or not".
 *
 *  - Anonymous:  Signup (-> /pricing)  + Signin (-> /sign-in)
 *  - Signed-in:  Sign out (returns to /)
 *
 * Signed-in users never see "Signin" — that link would force-redirect
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
          {!isSignedIn ? (
            <>
              {/* Signup -> /pricing (visitor picks a plan first). Signin ->
                  /sign-in (existing customers). Two filled buttons of equal
                  weight so neither disappears against the dark nav. */}
              <Link href="/pricing">
                <Button
                  size="sm"
                  className="border-0 bg-gradient-to-r from-amber-500 to-orange-600 font-semibold text-white hover:from-amber-600 hover:to-orange-700"
                >
                  Signup
                </Button>
              </Link>
              <Link href="/sign-in">
                <Button
                  size="sm"
                  className="border-0 bg-amber-500 font-semibold text-zinc-950 shadow-md shadow-amber-500/20 hover:bg-amber-400"
                >
                  <LogIn className="mr-1.5 h-4 w-4" />
                  Signin
                </Button>
              </Link>
            </>
          ) : (
            // Signed-in: only Sign out. Drops the visitor back at "/" as
            // anonymous so the Signup/Signin pair reappears.
            <SignOutButton redirectUrl="/">
              <Button
                size="sm"
                className="border-0 bg-amber-500 font-semibold text-zinc-950 shadow-md shadow-amber-500/20 hover:bg-amber-400"
              >
                <LogOut className="mr-1.5 h-4 w-4" />
                Sign out
              </Button>
            </SignOutButton>
          )}
        </div>
      </div>
    </nav>
  )
}
