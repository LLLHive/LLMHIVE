import type { Metadata } from "next"
import { ThemeProvider } from "@/components/theme-provider"

export const metadata: Metadata = {
  title: {
    default: "LLMHive - Multi-Model AI Orchestration Platform",
    template: "%s | LLMHive",
  },
  description:
    "LLMHive is a multi-model AI orchestration platform that routes every request to the best model for accuracy, speed, and cost.",
  openGraph: {
    title: "LLMHive - Multi-Model AI Orchestration Platform",
    description:
      "Route every request to the best model for accuracy, speed, and cost. LLMHive unifies 400+ models in one interface.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive - Multi-Model AI Orchestration Platform",
    description:
      "Route every request to the best model for accuracy, speed, and cost. LLMHive unifies 400+ models in one interface.",
  },
}

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="dark"
      enableSystem
      disableTransitionOnChange
    >
      {children}
    </ThemeProvider>
  )
}

