"use client"

import Link from "next/link"
import { SignOutButton } from "@clerk/nextjs"
import { LogIn, LogOut } from "lucide-react"
import { Button } from "@/components/ui/button"

/**
 * Auth controls for MarketingNav.
 *
 * Sign Up always routes to /sign-up. Clerk redirects new accounts to /pricing
 * after registration (see ClerkProvider + sign-up page).
 */
export function MarketingNavAuthButtons({ isSignedIn }: { isSignedIn: boolean }) {
  if (isSignedIn) {
    return (
      <SignOutButton redirectUrl="/">
        <Button
          size="sm"
          className="border-0 bg-amber-500 font-semibold text-zinc-950 shadow-md shadow-amber-500/20 hover:bg-amber-400"
        >
          <LogOut className="mr-1.5 h-4 w-4" />
          Sign Out
        </Button>
      </SignOutButton>
    )
  }

  return (
    <>
      <Button
        asChild
        size="sm"
        className="border-0 bg-gradient-to-r from-amber-500 to-orange-600 font-semibold text-white hover:from-amber-600 hover:to-orange-700"
      >
        <Link href="/sign-up">Sign Up</Link>
      </Button>
      <Button
        asChild
        size="sm"
        className="border-0 bg-amber-500 font-semibold text-zinc-950 shadow-md shadow-amber-500/20 hover:bg-amber-400"
      >
        <Link href="/sign-in">
          <LogIn className="mr-1.5 h-4 w-4" />
          Sign In
        </Link>
      </Button>
    </>
  )
}
