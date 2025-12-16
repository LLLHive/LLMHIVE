import type React from "react"
import type { Metadata } from "next"
import { Geist, Geist_Mono, Orbitron } from "next/font/google"
import "./globals.css"
import { AnalyticsWrapper } from "@/components/analytics"
import { Toaster } from "@/components/ui/sonner"
import { ThemeProvider } from "@/components/theme-provider"
import { AuthProvider } from "@/lib/auth-context"
import { AppearanceSettingsLoader } from "@/components/appearance-settings-loader"

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
    <html lang="en" suppressHydrationWarning>
      <body className={`font-sans antialiased ${orbitron.variable}`}>
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
  )
}
// Build trigger: 1765766573
