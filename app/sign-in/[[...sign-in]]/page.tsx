import { SignInClient } from "@/components/auth/sign-in-client"
import AppBackground from "@/components/branding/AppBackground"
import Image from "next/image"
import LogoText from "@/components/branding/LogoText"

export default function SignInPage() {
  return (
    // Page-level scroll only (no nested scroll context). See sign-up/page.tsx
    // for the full layout strategy notes.
    <div className="relative min-h-[100dvh] overflow-x-hidden">
      <AppBackground />

      <div className="relative z-10 flex min-h-[100dvh] flex-col items-center px-4 pt-[max(1.5rem,env(safe-area-inset-top,0px)+0.5rem)] pb-[max(1.5rem,env(safe-area-inset-bottom,0px)+1rem)]">
        {/* `my-auto` centers vertically when there's room and lets the
            page scroll naturally when content is taller than the viewport. */}
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
            <p className="mt-2 text-center text-sm text-zinc-400">
              Next-Generation AI Orchestration
            </p>
          </div>

          <div className="w-full pb-2">
            <SignInClient />
          </div>

          <p className="mt-6 text-center text-xs text-zinc-500 sm:mt-8">
            Protected by enterprise-grade security
          </p>
        </div>
      </div>
    </div>
  )
}

