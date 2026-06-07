import type { Metadata } from "next"
import { sitePath } from "@/lib/site-url"

export const metadata: Metadata = {
  title: "LLMHive Support Tickets",
  description: "Manage support tickets and request updates in LLMHive.",
  alternates: {
    canonical: sitePath('/support/tickets'),
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
          item: sitePath('/support/tickets'),
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
