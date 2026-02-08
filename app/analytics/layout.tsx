import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "LLMHive Analytics",
  description: "Monitor performance, feedback, and usage analytics in LLMHive.",
  alternates: {
    canonical: "https://www.llmhive.ai/analytics",
  },
  robots: {
    index: false,
    follow: false,
  },
  openGraph: {
    title: "LLMHive Analytics",
    description: "Monitor performance, feedback, and usage analytics in LLMHive.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive Analytics",
    description: "Monitor performance, feedback, and usage analytics in LLMHive.",
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
          name: "Analytics",
          item: "https://www.llmhive.ai/analytics",
        },
      ],
    },
  ],
}

export default function AnalyticsLayout({ children }: { children: React.ReactNode }) {
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
