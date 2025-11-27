import type React from "react"
import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import "./globals.css"
import { AnalyticsWrapper } from "@/components/analytics"

const _geist = Geist({ subsets: ["latin"] })
const _geistMono = Geist_Mono({ subsets: ["latin"] })

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
    <html lang="en" className="dark">
      <body className={`font-sans antialiased`}>
        {children}
        <AnalyticsWrapper />
      </body>
    </html>
  )
}
