import type { Metadata } from "next"
import { Suspense } from "react"
import { Loader2 } from "lucide-react"
import Ad4FreePricingClient from "./Ad4FreePricingClient"
import { sitePath } from "@/lib/site-url"

/**
 * Clone of /landing/grandmother-free for Ad4 campaign creatives.
 * Image order: Ad4 Image3 (hero) → Image2 (lifestyle) → Image1 (accent).
 */
export const metadata: Metadata = {
  title: "LLMHive — Premium orchestration for the best AI answers",
  description:
    "Route your requests across top models instantly. Start a 7-day Standard free trial ($0 today, no card required) or subscribe to Premium for $20/month.",
  alternates: {
    canonical: sitePath("/landing/ad4-free"),
  },
  openGraph: {
    title: "LLMHive — Premium orchestration for the best AI answers",
    description:
      "Better answers, lower cost, zero hassle. Try Standard free for 7 days with no card, or go Premium at $20/month.",
    type: "website",
    url: sitePath("/landing/ad4-free"),
    images: [
      {
        url: sitePath("/campaigns/ad4/lifestyle-scene-v2.png"),
        width: 1500,
        height: 1000,
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

export default function Ad4FreeLandingPage() {
  return (
    <Suspense fallback={<Fallback />}>
      <Ad4FreePricingClient />
    </Suspense>
  )
}
