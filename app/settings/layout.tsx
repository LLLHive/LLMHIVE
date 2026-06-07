import type { Metadata } from "next"
import { sitePath } from "@/lib/site-url"

export const metadata: Metadata = {
  title: "LLMHive Settings",
  description: "Manage account, billing, and preferences in LLMHive settings.",
  alternates: {
    canonical: sitePath('/settings'),
  },
  robots: {
    index: false,
    follow: false,
  },
  openGraph: {
    title: "LLMHive Settings",
    description: "Manage account, billing, and preferences in LLMHive settings.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive Settings",
    description: "Manage account, billing, and preferences in LLMHive settings.",
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
          name: "Settings",
          item: sitePath('/settings'),
        },
      ],
    },
  ],
}

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
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
