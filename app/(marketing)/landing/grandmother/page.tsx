import type { Metadata } from "next"
import { Suspense } from "react"
import { Loader2 } from "lucide-react"
import GrandmotherPricingClient from "./GrandmotherPricingClient"
import { sitePath } from "@/lib/site-url"

/**
 * Campaign pricing experience — visual theme from the Grandmother campaign mockup.
 * Checkout / Clerk / Stripe behavior mirrors /pricing. The original
 * app/pricing page is untouched.
 */
export const metadata: Metadata = {
  title: "LLMHive — Premium orchestration for the best AI answers",
  description:
    "Route your requests across top models instantly. Start a 3-day Standard free trial ($0 today, card required) or subscribe to Premium for $20/month.",
  alternates: {
    canonical: sitePath("/landing/grandmother"),
  },
  openGraph: {
    title: "LLMHive — Premium orchestration for the best AI answers",
    description:
      "Better answers, lower cost, zero hassle. Try Standard free for 3 days or go Premium at $20/month.",
    type: "website",
    url: sitePath("/landing/grandmother"),
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
      "Better answers, lower cost, zero hassle. Try Standard free for 3 days or go Premium at $20/month.",
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

export default function GrandmotherLandingPage() {
  return (
    <Suspense fallback={<Fallback />}>
      <GrandmotherPricingClient />
    </Suspense>
  )
}
