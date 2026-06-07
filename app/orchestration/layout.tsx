import type { Metadata } from "next"
import { sitePath } from "@/lib/site-url"

export const metadata: Metadata = {
  title: "LLMHive Orchestration",
  description:
    "Configure LLMHive orchestration, models, reasoning methods, and quality controls.",
  alternates: {
    canonical: sitePath('/orchestration'),
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
          item: sitePath('/orchestration'),
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
