import { SignUp } from "@clerk/nextjs"
import AppBackground from "@/components/branding/AppBackground"
import Image from "next/image"
import LogoText from "@/components/branding/LogoText"

export default function SignUpPage() {
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
          Join the AI Revolution
        </p>
      </div>
      
      {/* Clerk Sign Up Component */}
      <div className="z-10">
        <SignUp 
          appearance={{
            elements: {
              rootBox: "mx-auto",
              card: "bg-background/80 backdrop-blur-xl border border-white/10 shadow-2xl",
            }
          }}
          routing="path"
          path="/sign-up"
          signInUrl="/sign-in"
        />
      </div>
      
      {/* Footer */}
      <p className="text-xs text-muted-foreground mt-8 z-10">
        By signing up, you agree to our Terms of Service
      </p>
    </div>
  )
}

