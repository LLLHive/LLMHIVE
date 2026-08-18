import type { Metadata } from "next"
import { Suspense } from "react"
import { Loader2 } from "lucide-react"
import GrandmotherFreePricingClient from "./GrandmotherFreePricingClient"
import { sitePath } from "@/lib/site-url"

/**
 * Clone of /landing/grandmother for the no-card Standard trial campaign.
 * Do not edit the original grandmother landing — this file is independent.
 */
export const metadata: Metadata = {
  title: "LLMHive — Premium orchestration for the best AI answers",
  description:
    "Route your requests across top models instantly. Start a 3-day Standard free trial ($0 today, no card required) or subscribe to Premium for $20/month.",
  alternates: {
    canonical: sitePath("/landing/grandmother-free"),
  },
  openGraph: {
    title: "LLMHive — Premium orchestration for the best AI answers",
    description:
      "Better answers, lower cost, zero hassle. Try Standard free for 3 days with no card, or go Premium at $20/month.",
    type: "website",
    url: sitePath("/landing/grandmother-free"),
    images: [
      {
        url: sitePath("/campaigns/grandmother/lifestyle-scene.jpg"),
        width: 1024,
        height: 576,
        alt: "LLMHive — less time getting things done, more time for what matters",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive — Premium orchestration for the best AI answers",
    description:
      "Better answers, lower cost, zero hassle. Try Standard free for 3 days with no card, or go Premium at $20/month.",
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

export default function GrandmotherFreeLandingPage() {
  return (
    <Suspense fallback={<Fallback />}>
      <GrandmotherFreePricingClient />
    </Suspense>
  )
}
