import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "LLMHive Billing",
  description: "Manage subscriptions, usage, and billing details in LLMHive.",
  alternates: {
    canonical: "https://www.llmhive.ai/billing",
  },
  robots: {
    index: false,
    follow: false,
  },
  openGraph: {
    title: "LLMHive Billing",
    description: "Manage subscriptions, usage, and billing details in LLMHive.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive Billing",
    description: "Manage subscriptions, usage, and billing details in LLMHive.",
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
          name: "Billing",
          item: "https://www.llmhive.ai/billing",
        },
      ],
    },
  ],
}

export default function BillingLayout({ children }: { children: React.ReactNode }) {
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
