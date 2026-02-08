import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "LLMHive Orchestration",
  description:
    "Configure LLMHive orchestration, models, reasoning methods, and quality controls.",
  alternates: {
    canonical: "https://www.llmhive.ai/orchestration",
  },
  openGraph: {
    title: "LLMHive Orchestration",
    description:
      "Configure LLMHive orchestration, models, reasoning methods, and quality controls.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive Orchestration",
    description:
      "Configure LLMHive orchestration, models, reasoning methods, and quality controls.",
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
          name: "Orchestration",
          item: "https://www.llmhive.ai/orchestration",
        },
      ],
    },
  ],
}

export default function OrchestrationLayout({ children }: { children: React.ReactNode }) {
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
