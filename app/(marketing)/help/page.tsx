import type { Metadata } from "next"
import HelpClient from "./HelpClient"

export const metadata: Metadata = {
  title: "LLMHive Help Center",
  description:
    "Get answers on pricing, security, billing, and product usage in the LLMHive help center.",
  alternates: {
    canonical: "https://www.llmhive.ai/help",
  },
  openGraph: {
    title: "LLMHive Help Center",
    description:
      "Get answers on pricing, security, billing, and product usage in the LLMHive help center.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive Help Center",
    description:
      "Get answers on pricing, security, billing, and product usage in the LLMHive help center.",
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
            name: "Help Center",
            item: "https://www.llmhive.ai/help",
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

export default function HelpCenterPage() {
  return (
    <>
      {renderStructuredData()}
      <HelpClient />
    </>
  )
}
