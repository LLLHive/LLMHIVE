import type { Metadata } from "next"
import DemoClient from "./DemoClient"
import { getSiteUrl, sitePath } from "@/lib/site-url"
import { DEMO_VIDEO } from "@/lib/marketing/demo-video"
import { MARKETING_FEATURED_LINE } from "@/lib/marketing/featured-models"

const title = "LLMHive Product Demo"
const description = `Watch LLMHive route one question across ${MARKETING_FEATURED_LINE}. 60-second product demo.`

export const metadata: Metadata = {
  title,
  description,
  alternates: {
    canonical: sitePath("/demo"),
  },
  openGraph: {
    title,
    description,
    type: "website",
    url: sitePath("/demo"),
    images: [
      {
        url: sitePath(DEMO_VIDEO.poster),
        width: 1920,
        height: 1080,
        alt: "LLMHive product demo",
      },
    ],
    videos: [
      {
        url: sitePath(DEMO_VIDEO.src),
        width: 1920,
        height: 1080,
        type: "video/mp4",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title,
    description,
    images: [sitePath(DEMO_VIDEO.poster)],
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
            item: sitePath("/demo"),
          },
        ],
      },
      {
        "@type": "VideoObject",
        name: DEMO_VIDEO.title,
        description: DEMO_VIDEO.description,
        thumbnailUrl: sitePath(DEMO_VIDEO.poster),
        contentUrl: sitePath(DEMO_VIDEO.src),
        embedUrl: sitePath("/demo"),
        uploadDate: "2026-08-18",
        duration: "PT48S",
        publisher: {
          "@type": "Organization",
          name: "LLMHive",
          url: getSiteUrl(),
        },
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
