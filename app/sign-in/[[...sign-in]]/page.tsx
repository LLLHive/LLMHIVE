import { SignIn } from "@clerk/nextjs"
import AppBackground from "@/components/branding/AppBackground"
import Image from "next/image"
import LogoText from "@/components/branding/LogoText"
import { ClerkLocalhostBlockedMessage } from "@/components/auth/clerk-localhost-blocked"
import { isProductionClerkKeyOnLocalDev } from "@/lib/clerk-local-dev"

export default function SignInPage() {
  const clerkBlockedOnLocal = isProductionClerkKeyOnLocalDev()

  return (
    <div className="relative flex min-h-[100dvh] flex-col overflow-x-hidden overflow-y-auto overscroll-y-contain">
      <AppBackground />

      <div className="relative z-10 flex flex-1 flex-col items-center px-4 py-8 pb-[max(1.5rem,env(safe-area-inset-bottom,0px)+1rem)] pt-[max(1.5rem,env(safe-area-inset-top,0px)+0.5rem)] sm:justify-center sm:py-10">
        {/* Logo — compact on small viewports so the card never clips */}
        <div className="mb-6 flex shrink-0 flex-col items-center sm:mb-8">
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

        {/* Card: scroll inside if content is tall (keyboard / small phones) */}
        <div className="w-full max-w-md shrink-0 pb-2">
          {clerkBlockedOnLocal ? (
            <div className="max-h-[min(70dvh,calc(100dvh-14rem))] overflow-y-auto pr-0.5 [-webkit-overflow-scrolling:touch]">
              <ClerkLocalhostBlockedMessage mode="sign-in" />
            </div>
          ) : (
            <SignIn
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
              path="/sign-in"
              signUpUrl="/sign-up"
            />
          )}
        </div>

        <p className="mt-auto shrink-0 pt-6 text-center text-xs text-zinc-500 sm:mt-8 sm:pt-0">
          Protected by enterprise-grade security
        </p>
      </div>
    </div>
  )
}

