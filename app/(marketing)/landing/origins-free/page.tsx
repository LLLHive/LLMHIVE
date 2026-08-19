import type { Metadata } from "next"
import { Suspense } from "react"
import { Loader2 } from "lucide-react"
import OriginsFreePricingClient from "./OriginsFreePricingClient"
import { sitePath } from "@/lib/site-url"

/**
 * Clone of /landing/origins for the no-card Standard trial campaign.
 * Do not edit the original origins landing — this file is independent.
 */
export const metadata: Metadata = {
  title: "LLMHive — Premium orchestration for the best AI answers",
  description:
    "Route your requests across top models instantly. Start a 7-day Standard free trial ($0 today, no card required) or subscribe to Premium for $20/month.",
  alternates: {
    canonical: sitePath("/landing/origins-free"),
  },
  openGraph: {
    title: "LLMHive — Premium orchestration for the best AI answers",
    description:
      "Better answers, lower cost, zero hassle. Try Standard free for 7 days with no card, or go Premium at $20/month.",
    type: "website",
    url: sitePath("/landing/origins-free"),
    images: [
      {
        url: sitePath("/campaigns/origins/lifestyle-scene.jpg"),
        width: 1920,
        height: 887,
        alt: "LLMHive — less time getting things done, more time for what matters",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive — Premium orchestration for the best AI answers",
    description:
      "Better answers, lower cost, zero hassle. Try Standard free for 7 days with no card, or go Premium at $20/month.",
  },
  robots: { index: true, follow: true },
}

function Fallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center bg-[#050505]">
      <Loader2 className="h-8 w-8 animate-spin text-amber-500" aria-label="Loading" />
    </div>
  )
}

export default function OriginsFreeLandingPage() {
  return (
    <Suspense fallback={<Fallback />}>
      <OriginsFreePricingClient />
    </Suspense>
  )
}
