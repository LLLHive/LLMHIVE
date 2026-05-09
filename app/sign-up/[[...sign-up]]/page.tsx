import { SignUp } from "@clerk/nextjs"
import AppBackground from "@/components/branding/AppBackground"
import Image from "next/image"
import LogoText from "@/components/branding/LogoText"
import { ClerkLocalhostBlockedMessage } from "@/components/auth/clerk-localhost-blocked"
import { isProductionClerkKeyOnLocalDev } from "@/lib/clerk-local-dev"

export default function SignUpPage() {
  const clerkBlockedOnLocal = isProductionClerkKeyOnLocalDev()

  return (
    // Page-level scroll: only the document scrolls (no nested scroll context).
    // overflow-x-hidden prevents horizontal jitter from background art.
    <div className="relative min-h-[100dvh] overflow-x-hidden">
      <AppBackground />

      {/*
        Layout strategy:
        - Outer flex column with min-h-[100dvh] makes the page exactly the
          viewport height when content fits, and grows naturally when content
          is taller (e.g. tall Clerk form on small phones, or with the soft
          keyboard up).
        - The inner content wrapper uses `my-auto` so it vertically centers
          when there's room, but stays at the top and lets the page scroll
          naturally when content overflows. This avoids the
          "centered content clipped above the scroll viewport" bug.
        - safe-area paddings keep things clear of iOS notches and home bars.
      */}
      <div className="relative z-10 flex min-h-[100dvh] flex-col items-center px-4 pt-[max(1.5rem,env(safe-area-inset-top,0px)+0.5rem)] pb-[max(1.5rem,env(safe-area-inset-bottom,0px)+1rem)]">
        <div className="my-auto flex w-full max-w-md flex-col items-center py-6 sm:py-10">
          <div className="mb-6 flex flex-col items-center sm:mb-8">
            <Image
              src="/logo.png"
              alt="LLMHive Logo"
              width={80}
              height={80}
              className="mb-3 h-auto w-auto max-h-[72px] max-w-[72px] sm:mb-4 sm:max-h-[80px] sm:max-w-[80px]"
              priority
            />
            <LogoText height={40} variant="title" />
            <p className="mt-2 text-center text-sm text-zinc-400">Join the AI Revolution</p>
          </div>

          <div className="w-full pb-2">
            {clerkBlockedOnLocal ? (
              <ClerkLocalhostBlockedMessage mode="sign-up" />
            ) : (
              <SignUp
                appearance={{
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
                }}
                routing="path"
                path="/sign-up"
                signInUrl="/sign-in"
                forceRedirectUrl="/pricing"
              />
            )}
          </div>

          <p className="mt-6 text-center text-xs text-zinc-500 sm:mt-8">
            By signing up, you agree to our Terms of Service
          </p>
        </div>
      </div>
    </div>
  )
}

