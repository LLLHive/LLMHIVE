import type { Metadata } from "next"
import PricingClient from "./PricingClient"

export const metadata: Metadata = {
  title: "LLMHive Pricing",
  description:
    "Compare LLMHive pricing tiers, ELITE query limits, and enterprise features.",
  alternates: {
    canonical: "https://www.llmhive.ai/pricing",
  },
  openGraph: {
    title: "LLMHive Pricing",
    description:
      "Compare LLMHive pricing tiers, ELITE query limits, and enterprise features.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive Pricing",
    description:
      "Compare LLMHive pricing tiers, ELITE query limits, and enterprise features.",
  },
}

function renderStructuredData() {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "Pricing",
            item: "https://www.llmhive.ai/pricing",
          },
        ],
      },
    ],
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
    />
  )
}

export default function PricingPage() {
  return (
    <>
      {renderStructuredData()}
      <PricingClient />
    </>
  )
}
