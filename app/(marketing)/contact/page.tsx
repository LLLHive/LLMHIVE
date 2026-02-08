import type { Metadata } from "next"
import ContactClient from "./ContactClient"

export const metadata: Metadata = {
  title: "Contact LLMHive",
  description:
    "Contact the LLMHive team for support, partnerships, or enterprise inquiries.",
  alternates: {
    canonical: "https://www.llmhive.ai/contact",
  },
  openGraph: {
    title: "Contact LLMHive",
    description:
      "Contact the LLMHive team for support, partnerships, or enterprise inquiries.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Contact LLMHive",
    description:
      "Contact the LLMHive team for support, partnerships, or enterprise inquiries.",
  },
}

function renderStructuredData() {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "Contact",
            item: "https://www.llmhive.ai/contact",
          },
        ],
      },
    ],
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
    />
  )
}

export default function ContactPage() {
  return (
    <>
      {renderStructuredData()}
      <ContactClient />
    </>
  )
}

