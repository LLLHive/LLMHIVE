import type { Metadata } from "next"
import { Suspense } from "react"
import { Loader2 } from "lucide-react"
import NoCardCampaignPricingClient from "@/components/marketing/NoCardCampaignPricingClient"
import {
  getNoCardCampaignLanding,
  type NoCardCampaignLandingConfig,
} from "@/lib/marketing/no-card-campaign-landings"
import { sitePath } from "@/lib/site-url"

function buildMetadata(config: NoCardCampaignLandingConfig): Metadata {
  return {
    title: config.metaTitle,
    description: config.metaDescription,
    alternates: {
      canonical: sitePath(config.campaignPath),
    },
    openGraph: {
      title: config.metaTitle,
      description: config.metaDescription,
      type: "website",
      url: sitePath(config.campaignPath),
      images: [
        {
          url: sitePath(config.heroImageSrc),
          width: 1920,
          height: 1080,
          alt: config.heroImageAlt,
        },
      ],
    },
    twitter: {
      card: "summary_large_image",
      title: config.metaTitle,
      description: config.metaDescription,
    },
    robots: { index: true, follow: true },
  }
}

function Fallback() {
  return (
    <div className="flex min-h-[40vh] items-center justify-center bg-[#050505]">
      <Loader2 className="h-8 w-8 animate-spin text-amber-500" aria-label="Loading" />
    </div>
  )
}

export function createNoCardCampaignPage(slug: string) {
  const config = getNoCardCampaignLanding(slug)
  if (!config) {
    throw new Error(`Unknown no-card campaign landing: ${slug}`)
  }

  const landingConfig = config
  const metadata = buildMetadata(landingConfig)

  function NoCardCampaignLandingPage() {
    return (
      <Suspense fallback={<Fallback />}>
        <NoCardCampaignPricingClient config={landingConfig} />
      </Suspense>
    )
  }

  return { metadata, default: NoCardCampaignLandingPage }
}
