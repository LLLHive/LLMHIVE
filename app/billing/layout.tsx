import type { Metadata } from "next"
import { sitePath } from "@/lib/site-url"

export const metadata: Metadata = {
  title: "LLMHive Billing",
  description: "Manage subscriptions, usage, and billing details in LLMHive.",
  alternates: {
    canonical: sitePath('/billing'),
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
          item: sitePath('/billing'),
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
