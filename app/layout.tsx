import type React from "react"
import type { Metadata } from "next"
import { Geist, Geist_Mono, Orbitron } from "next/font/google"
import "./globals.css"
import { ClerkProvider } from "@clerk/nextjs"
import { AnalyticsWrapper } from "@/components/analytics"
import { Toaster } from "@/components/ui/sonner"
import { ThemeProvider } from "@/components/theme-provider"
import { AuthProvider } from "@/lib/auth-context"
import { AppearanceSettingsLoader } from "@/components/appearance-settings-loader"
import AppBackground from "@/components/branding/AppBackground"
import { ForestBackgroundWrapper } from "@/components/forest-background-wrapper"

const _geist = Geist({ subsets: ["latin"] })
const _geistMono = Geist_Mono({ subsets: ["latin"] })
const orbitron = Orbitron({ 
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["400", "500", "600", "700", "800", "900"]
})

export const metadata: Metadata = {
  title: "LLMHive - Next-Generation AI Assistant",
  description: "Premium AI assistant interface powered by advanced language models",
  generator: "v0.app",
  icons: {
    icon: [
      {
        url: "/logo.png",
      },
    ],
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <ClerkProvider
      signUpForceRedirectUrl="/pricing"
      afterSignUpUrl="/pricing"
      signInFallbackRedirectUrl="/"
      appearance={{
        variables: {
          colorPrimary: "#cd7f32", // Bronze/gold brand color
          colorBackground: "#0f0f0f",
          colorInputBackground: "#1a1a1a",
          colorInputText: "#ffffff",
          colorText: "#ffffff",
          colorTextSecondary: "#a1a1aa",
          borderRadius: "0.5rem",
        },
        elements: {
          formButtonPrimary: "bg-[#cd7f32] hover:bg-[#b8860b] text-white",
          card: "bg-[#0f0f0f] border border-white/10",
          headerTitle: "text-white",
          headerSubtitle: "text-zinc-400",
          socialButtonsBlockButton: "border-white/20 text-white hover:bg-white/5",
          formFieldLabel: "text-zinc-300",
          formFieldInput: "bg-[#1a1a1a] border-white/10 text-white",
          footerActionLink: "text-[#cd7f32] hover:text-[#b8860b]",
          // OTP code input boxes with visible orange border
          otpCodeFieldInput: "!border-2 !border-[#cd7f32] !bg-[#1a1a1a] !text-white",
          otpCodeField: "gap-2",
        },
      }}
    >
      <html lang="en" suppressHydrationWarning>
        <head>
          <script
            dangerouslySetInnerHTML={{
              __html: `
                (function() {
                  try {
                    var theme = localStorage.getItem('theme');
                    var systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                    var useDark =
                      theme === 'dark' ||
                      (theme === 'system' && systemDark) ||
                      (!theme && systemDark);
                    document.documentElement.classList.toggle('dark', !!useDark);
                  } catch (e) {}
                })();
              `,
            }}
          />
        </head>
        <body className={`min-h-screen bg-transparent text-foreground font-sans antialiased ${orbitron.variable}`}>
          <AppBackground />
          <ForestBackgroundWrapper />
          <ThemeProvider
            attribute="class"
            defaultTheme="dark"
            enableSystem
            disableTransitionOnChange={false}
          >
            <AuthProvider>
              <AppearanceSettingsLoader />
              {children}
              <Toaster 
                position="bottom-right"
                closeButton
                richColors
                expand={false}
                toastOptions={{
                  duration: 4000,
                }}
              />
              <AnalyticsWrapper />
            </AuthProvider>
          </ThemeProvider>
        </body>
      </html>
    </ClerkProvider>
  )
}
// Build trigger: 1765766573
