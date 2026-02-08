import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "LLMHive Support Tickets",
  description: "Manage support tickets and request updates in LLMHive.",
  alternates: {
    canonical: "https://www.llmhive.ai/support/tickets",
  },
  robots: {
    index: false,
    follow: false,
  },
  openGraph: {
    title: "LLMHive Support Tickets",
    description: "Manage support tickets and request updates in LLMHive.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive Support Tickets",
    description: "Manage support tickets and request updates in LLMHive.",
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
          name: "Support Tickets",
          item: "https://www.llmhive.ai/support/tickets",
        },
      ],
    },
  ],
}

export default function SupportTicketsLayout({ children }: { children: React.ReactNode }) {
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
