import type { Metadata } from "next"
import { getSiteUrl } from "@/lib/site-url"

export function buildBusinessMetadata(
  title: string,
  description: string,
  canonicalPath?: string
): Metadata {
  return {
    title: `${title} | LLMHive`,
    description,
    alternates: canonicalPath
      ? {
          canonical: `${getSiteUrl()}${canonicalPath}`,
        }
      : undefined,
    openGraph: {
      title: `${title} | LLMHive`,
      description,
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: `${title} | LLMHive`,
      description,
    },
  }
}
