import type { Metadata } from "next"
import DemoClient from "./DemoClient"

export const metadata: Metadata = {
  title: "LLMHive Product Demo",
  description:
    "Watch a full product demo of LLMHive multi-model orchestration, ELITE mode, and analytics.",
  alternates: {
    canonical: "https://www.llmhive.ai/demo",
  },
  openGraph: {
    title: "LLMHive Product Demo",
    description:
      "Watch a full product demo of LLMHive multi-model orchestration, ELITE mode, and analytics.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive Product Demo",
    description:
      "Watch a full product demo of LLMHive multi-model orchestration, ELITE mode, and analytics.",
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
            name: "Demo",
            item: "https://www.llmhive.ai/demo",
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

export default function DemoPage() {
  return (
    <>
      {renderStructuredData()}
      <DemoClient />
    </>
  )
}
