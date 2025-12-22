import { SignIn } from "@clerk/nextjs"
import AppBackground from "@/components/branding/AppBackground"
import Image from "next/image"
import LogoText from "@/components/branding/LogoText"

export default function SignInPage() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center relative">
      <AppBackground />
      
      {/* Logo and Branding */}
      <div className="flex flex-col items-center mb-8 z-10">
        <Image
          src="/logo.png"
          alt="LLMHive Logo"
          width={80}
          height={80}
          className="mb-4"
          priority
        />
        <LogoText height={40} variant="title" />
        <p className="text-sm text-muted-foreground mt-2">
          Next-Generation AI Orchestration
        </p>
      </div>
      
      {/* Clerk Sign In Component */}
      <div className="z-10">
        <SignIn 
          appearance={{
            elements: {
              rootBox: "mx-auto",
              card: "bg-background/80 backdrop-blur-xl border border-white/10 shadow-2xl",
            }
          }}
          routing="path"
          path="/sign-in"
          signUpUrl="/sign-up"
        />
      </div>
      
      {/* Footer */}
      <p className="text-xs text-muted-foreground mt-8 z-10">
        Protected by enterprise-grade security
      </p>
    </div>
  )
}

