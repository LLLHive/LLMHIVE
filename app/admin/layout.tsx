import type { Metadata } from "next"
import { sitePath } from "@/lib/site-url"

export const metadata: Metadata = {
  title: "LLMHive Admin",
  description: "Administrative dashboards and controls for LLMHive.",
  alternates: {
    canonical: sitePath('/admin'),
  },
  robots: {
    index: false,
    follow: false,
  },
  openGraph: {
    title: "LLMHive Admin",
    description: "Administrative dashboards and controls for LLMHive.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive Admin",
    description: "Administrative dashboards and controls for LLMHive.",
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
          name: "Admin",
          item: sitePath('/admin'),
        },
      ],
    },
  ],
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
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
