import type React from "react"
import type { Metadata } from "next"
import { Geist, Geist_Mono, Orbitron } from "next/font/google"
import "./globals.css"
import { ClerkProvider } from "@clerk/nextjs"
import { AnalyticsWrapper } from "@/components/analytics"
import { Toaster } from "@/components/ui/sonner"
import { ThemeProvider } from "@/components/theme-provider"
import { AuthProvider } from "@/lib/auth-context"
import { ConversationsProvider } from "@/lib/conversations-context"
import { AppearanceSettingsLoader } from "@/components/appearance-settings-loader"
import AppBackground from "@/components/branding/AppBackground"
import { ForestBackgroundWrapper } from "@/components/forest-background-wrapper"
import { SupportWidget } from "@/components/support-widget"

const _geist = Geist({ subsets: ["latin"] })
const _geistMono = Geist_Mono({ subsets: ["latin"] })
const orbitron = Orbitron({ 
  subsets: ["latin"],
  variable: "--font-display",
  weight: ["400", "500", "600", "700", "800", "900"]
})

const verification = (() => {
  const other: Record<string, string> = {}
  if (process.env.NEXT_PUBLIC_BING_SITE_VERIFICATION) {
    other["msvalidate.01"] = process.env.NEXT_PUBLIC_BING_SITE_VERIFICATION
  }
  if (process.env.NEXT_PUBLIC_BAIDU_SITE_VERIFICATION) {
    other["baidu-site-verification"] = process.env.NEXT_PUBLIC_BAIDU_SITE_VERIFICATION
  }

  const verificationData: Metadata["verification"] = {}
  if (process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION) {
    verificationData.google = process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION
  }
  if (process.env.NEXT_PUBLIC_YANDEX_SITE_VERIFICATION) {
    verificationData.yandex = process.env.NEXT_PUBLIC_YANDEX_SITE_VERIFICATION
  }
  if (Object.keys(other).length > 0) {
    verificationData.other = other
  }

  return Object.keys(verificationData).length > 0 ? verificationData : undefined
})()

export const metadata: Metadata = {
  metadataBase: new URL("https://www.llmhive.ai"),
  title: "LLMHive - Multi-Model AI Orchestration Platform",
  description:
    "LLMHive is a multi-model AI orchestration platform that routes every request to the best model for accuracy, speed, and cost. Built for teams and enterprises.",
  applicationName: "LLMHive",
  generator: "v0.app",
  alternates: {
    canonical: "https://www.llmhive.ai",
  },
  keywords: [
    "AI orchestration",
    "multi-model AI",
    "AI model router",
    "AI assistant platform",
    "enterprise AI",
    "LLM routing",
    "agentic AI",
    "AI productivity",
    "RAG platform",
    "AI model marketplace",
  ],
  openGraph: {
    title: "LLMHive - Multi-Model AI Orchestration Platform",
    description:
      "Route every request to the best model for accuracy, speed, and cost. LLMHive unifies 400+ models in one interface.",
    url: "https://www.llmhive.ai",
    siteName: "LLMHive",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive - Multi-Model AI Orchestration Platform",
    description:
      "Route every request to the best model for accuracy, speed, and cost. LLMHive unifies 400+ models in one interface.",
  },
  icons: {
    icon: [
      {
        url: "/logo.png",
      },
    ],
  },
  verification,
}

const websiteStructuredData = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: "LLMHive",
  url: "https://www.llmhive.ai",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <ClerkProvider
      signUpForceRedirectUrl="/pricing"
      signUpFallbackRedirectUrl="/pricing"
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
          <meta
            name="viewport"
            content="width=device-width, initial-scale=1, maximum-scale=5, viewport-fit=cover"
          />
          <script
            type="application/ld+json"
            dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteStructuredData) }}
          />
          {process.env.NEXT_PUBLIC_GA_ID ? (
            <>
              <script async src={`https://www.googletagmanager.com/gtag/js?id=${process.env.NEXT_PUBLIC_GA_ID}`} />
              <script
                dangerouslySetInnerHTML={{
                  __html: `
                    window.dataLayer = window.dataLayer || [];
                    function gtag(){dataLayer.push(arguments);}
                    gtag('js', new Date());
                    gtag('config', '${process.env.NEXT_PUBLIC_GA_ID}', {
                      anonymize_ip: true,
                    });
                  `,
                }}
              />
            </>
          ) : null}
          {process.env.NEXT_PUBLIC_META_PIXEL_ID ? (
            <script
              dangerouslySetInnerHTML={{
                __html: `
                  !function(f,b,e,v,n,t,s)
                  {if(f.fbq)return;n=f.fbq=function(){n.callMethod?
                  n.callMethod.apply(n,arguments):n.queue.push(arguments)};
                  if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
                  n.queue=[];t=b.createElement(e);t.async=!0;
                  t.src=v;s=b.getElementsByTagName(e)[0];
                  s.parentNode.insertBefore(t,s)}(window, document,'script',
                  'https://connect.facebook.net/en_US/fbevents.js');
                  fbq('init', '${process.env.NEXT_PUBLIC_META_PIXEL_ID}');
                  fbq('track', 'PageView');
                `,
              }}
            />
          ) : null}
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
              <ConversationsProvider>
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
                <SupportWidget />
              </ConversationsProvider>
            </AuthProvider>
          </ThemeProvider>
        </body>
      </html>
    </ClerkProvider>
  )
}
// Build trigger: 1765766573
