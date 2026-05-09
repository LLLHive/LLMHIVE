import Image from "next/image"
import Link from "next/link"
import { auth } from "@clerk/nextjs/server"
import { ArrowRight, LogIn } from "lucide-react"
import { Button } from "@/components/ui/button"
import { getPaidEntitlementFast } from "@/lib/billing/entitlement"

/**
 * Shared marketing-site header.
 *
 * Renders on every public page (`/`, `/pricing`, `/about`, all of
 * `app/(marketing)/*`) so anonymous visitors always have a clear way to sign
 * in or sign up — and signed-in visitors always have a clear way back into
 * the app without bouncing through the entitlement gate.
 *
 * Auth-state behaviour:
 *  - Not signed in     -> Signup (-> /pricing) + Signin (-> /sign-in)
 *  - Signed in + paid  -> Open app (-> /app)
 *  - Signed in + unpaid -> Choose your plan (-> /pricing)
 *    (We never link signed-in unpaid users back to /sign-in or /app, because
 *    Clerk would force-redirect them to /app and the gate would bounce them
 *    to /pricing — visually a redirect loop.)
 */
export async function MarketingNav() {
  const { userId } = await auth()
  const isSignedIn = Boolean(userId)

  let signedInPrimary: { href: string; label: string } | null = null
  if (isSignedIn && userId) {
    const ent = await getPaidEntitlementFast(userId)
    signedInPrimary = ent.hasPaidAccess
      ? { href: "/app", label: "Open app" }
      : { href: "/pricing", label: "Choose your plan" }
  }

  return (
    <nav className="fixed inset-x-0 top-0 z-50 border-b border-white/5 bg-black/60 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Link href="/" className="flex items-center gap-2.5">
          <Image src="/logo.png" alt="LLMHive" width={32} height={32} priority className="h-8 w-8" />
          <Image
            src="/brand/llmhive-wordmark-nav.png"
            alt="LLMHive"
            width={140}
            height={30}
            priority
            className="hidden h-6 w-auto sm:block"
          />
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
              {/* Signup goes to /pricing (the user picks a plan first); Signin
                  goes to /sign-in (existing customers). Both are filled
                  buttons of equal weight so neither disappears against the
                  dark nav. */}
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
            signedInPrimary && (
              <Link href={signedInPrimary.href}>
                <Button
                  size="sm"
                  className="border-0 bg-gradient-to-r from-amber-500 to-orange-600 text-white hover:from-amber-600 hover:to-orange-700"
                >
                  {signedInPrimary.label}
                  <ArrowRight className="ml-1.5 h-4 w-4" />
                </Button>
              </Link>
            )
          )}
        </div>
      </div>
    </nav>
  )
}
