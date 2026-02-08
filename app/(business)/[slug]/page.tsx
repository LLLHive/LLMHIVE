import { notFound } from "next/navigation"
import type { Metadata } from "next"
import PageShell from "@/components/business/PageShell"
import { businessPages } from "../content"

type PageProps = {
  params: { slug: string }
}

export function generateStaticParams() {
  return Object.keys(businessPages).map((slug) => ({ slug }))
}

export function generateMetadata({ params }: PageProps): Metadata {
  const page = businessPages[params.slug]
  if (!page) {
    return { title: "LLMHive" }
  }
  return {
    title: `${page.title} | LLMHive`,
    description: page.subtitle,
    alternates: {
      canonical: `https://www.llmhive.ai/${params.slug}`,
    },
    openGraph: {
      title: `${page.title} | LLMHive`,
      description: page.subtitle,
      type: "website",
    },
    twitter: {
      card: "summary_large_image",
      title: `${page.title} | LLMHive`,
      description: page.subtitle,
    },
  }
}

export default function BusinessPage({ params }: PageProps) {
  const page = businessPages[params.slug]
  if (!page) {
    notFound()
  }

  return (
    <PageShell
      title={page.title}
      subtitle={page.subtitle}
      sections={page.sections}
      ctaLabel={page.ctaLabel}
      ctaHref={page.ctaHref}
      breadcrumb={{ name: page.title, path: `/${params.slug}` }}
    />
  )
}
