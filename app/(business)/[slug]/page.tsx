import { notFound } from "next/navigation"
import type { Metadata } from "next"
import PageShell from "@/components/business/PageShell"
import { businessPages } from "../content"

type PageProps = {
  params: Promise<{ slug: string }>
}

export function generateStaticParams() {
  return Object.keys(businessPages).map((slug) => ({ slug }))
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params
  const page = businessPages[slug]
  if (!page) {
    return { title: "LLMHive" }
  }
  return {
    title: `${page.title} | LLMHive`,
    description: page.subtitle,
    alternates: {
      canonical: `https://llmhive.ai/${slug}`,
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

export default async function BusinessPage({ params }: PageProps) {
  const { slug } = await params
  const page = businessPages[slug]
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
      breadcrumb={{ name: page.title, path: `/${slug}` }}
    />
  )
}
