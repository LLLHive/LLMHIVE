import type { Metadata } from "next"
import PromoClient from "./PromoClient"

export const metadata: Metadata = {
  title: "LLMHive Promo",
  description:
    "Premium LLMHive promo experience featuring patented orchestration, benchmarks, and pricing.",
  alternates: {
    canonical: "https://www.llmhive.ai/promo",
  },
  openGraph: {
    title: "LLMHive Promo",
    description:
      "Premium LLMHive promo experience featuring patented orchestration, benchmarks, and pricing.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive Promo",
    description:
      "Premium LLMHive promo experience featuring patented orchestration, benchmarks, and pricing.",
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
            name: "Promo",
            item: "https://www.llmhive.ai/promo",
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

export default function PromoLandingPage() {
  return (
    <>
      {renderStructuredData()}
      <PromoClient />
    </>
  )
}
