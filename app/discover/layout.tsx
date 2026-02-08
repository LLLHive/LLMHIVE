import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "LLMHive Discover",
  description:
    "Discover templates, knowledge resources, and curated workflows in LLMHive.",
  alternates: {
    canonical: "https://www.llmhive.ai/discover",
  },
  openGraph: {
    title: "LLMHive Discover",
    description:
      "Discover templates, knowledge resources, and curated workflows in LLMHive.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive Discover",
    description:
      "Discover templates, knowledge resources, and curated workflows in LLMHive.",
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
          name: "Discover",
          item: "https://www.llmhive.ai/discover",
        },
      ],
    },
  ],
}

export default function DiscoverLayout({ children }: { children: React.ReactNode }) {
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
