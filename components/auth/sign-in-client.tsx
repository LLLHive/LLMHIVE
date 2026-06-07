"use client"

import { Suspense } from "react"
import { useSearchParams } from "next/navigation"
import { SignIn } from "@clerk/nextjs"
import { ClerkLocalhostBlockedMessage } from "@/components/auth/clerk-localhost-blocked"
import { isProductionClerkKeyOnLocalDev } from "@/lib/clerk-local-dev"

const signInAppearance = {
  elements: {
    rootBox: "mx-auto w-full",
    card: "bg-background/80 backdrop-blur-xl border border-white/10 shadow-2xl",
    socialButtonsBlockButton: "flex-1",
    socialButtonsProviderIcon__apple: "!text-white !fill-white [&_path]:!fill-white",
    socialButtonsBlockButtonText__apple: "!text-white",
    socialButtonsIconButton: "hover:bg-white/10 [&_svg]:text-white",
    socialButtonsIconButton__apple: "[&_svg]:!text-white [&_svg]:!fill-white [&_path]:!fill-white",
    otpCodeFieldInput: "!border-2 !border-[#cd7f32] !bg-[#1a1a1a] !text-white",
    otpCodeField: "gap-2",
    formFieldInput: "border border-gray-600 bg-background/50",
  },
} as const

/** Only allow same-origin relative paths (blocks open-redirect via query param). */
function safeRedirectUrl(value: string | null): string | undefined {
  if (!value) return undefined
  const trimmed = value.trim()
  if (!trimmed.startsWith("/") || trimmed.startsWith("//")) return undefined
  return trimmed
}

function SignInWithRedirect() {
  const searchParams = useSearchParams()
  const redirectUrl = safeRedirectUrl(searchParams.get("redirect_url"))
  const clerkBlockedOnLocal = isProductionClerkKeyOnLocalDev()

  if (clerkBlockedOnLocal) {
    return <ClerkLocalhostBlockedMessage mode="sign-in" />
  }

  return (
    <SignIn
      appearance={signInAppearance}
      routing="path"
      path="/sign-in"
      signUpUrl="/sign-up"
      {...(redirectUrl
        ? {
            forceRedirectUrl: redirectUrl,
            fallbackRedirectUrl: redirectUrl,
          }
        : {})}
    />
  )
}

export function SignInClient() {
  return (
    <Suspense fallback={null}>
      <SignInWithRedirect />
    </Suspense>
  )
}
