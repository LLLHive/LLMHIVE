import type { Metadata } from "next"
import { sitePath } from "@/lib/site-url"

export const metadata: Metadata = {
  title: "LLMHive Models",
  description:
    "Explore LLMHive model rankings, pricing, and capabilities across leading providers.",
  alternates: {
    canonical: sitePath('/models'),
  },
  openGraph: {
    title: "LLMHive Models",
    description:
      "Explore LLMHive model rankings, pricing, and capabilities across leading providers.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive Models",
    description:
      "Explore LLMHive model rankings, pricing, and capabilities across leading providers.",
  },
}

const structuredData = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "BreadcrumbList",
      itemListElement: [
        {
          "@type": "ListItem",
          position: 1,
          name: "Models",
          item: sitePath('/models'),
        },
      ],
    },
  ],
}

export default function ModelsLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
      />
      {children}
    </>
  )
}
