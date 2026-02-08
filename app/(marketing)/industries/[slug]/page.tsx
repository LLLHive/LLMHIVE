import { notFound } from "next/navigation"
import type { Metadata } from "next"
import Link from "next/link"
import { industryFaqs } from "../content"

type PageProps = {
  params: { slug: string }
}

export function generateStaticParams() {
  return industryFaqs.map((item) => ({ slug: item.slug }))
}

export function generateMetadata({ params }: PageProps): Metadata {
  const page = industryFaqs.find((item) => item.slug === params.slug)
  if (!page) {
    return { title: "LLMHive" }
  }
  return {
    title: page.title,
    description: page.description,
    openGraph: {
      title: page.title,
      description: page.description,
      type: "article",
    },
    twitter: {
      card: "summary_large_image",
      title: page.title,
      description: page.description,
    },
  }
}

function renderStructuredData(page: (typeof industryFaqs)[number]) {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "FAQPage",
        mainEntity: page.faqs.map((item) => ({
          "@type": "Question",
          name: item.question,
          acceptedAnswer: {
            "@type": "Answer",
            text: item.answer,
          },
        })),
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "Industries",
            item: "https://www.llmhive.ai/industries",
          },
          {
            "@type": "ListItem",
            position: 2,
            name: page.title,
            item: `https://www.llmhive.ai/industries/${page.slug}`,
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

export default function IndustryFaqPage({ params }: PageProps) {
  const page = industryFaqs.find((item) => item.slug === params.slug)
  if (!page) {
    notFound()
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      {renderStructuredData(page)}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <p className="text-sm text-muted-foreground">Industry FAQ</p>
          <h1 className="text-3xl md:text-4xl font-bold">{page.title}</h1>
          <p className="mt-2 text-muted-foreground">{page.description}</p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-12 space-y-6">
        {page.faqs.map((item) => (
          <section key={item.question} className="rounded-2xl border border-border/60 bg-card/40 p-6">
            <h2 className="text-lg font-semibold">{item.question}</h2>
            <p className="mt-3 text-sm text-muted-foreground">{item.answer}</p>
          </section>
        ))}

        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Next Steps</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Explore industry comparisons and role-based guides.
          </p>
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <Link href="/comparisons/industries" className="text-[var(--bronze)]">
              Industry Comparisons →
            </Link>
            <Link href="/comparisons" className="text-[var(--bronze)]">
              All Comparisons →
            </Link>
            <Link href="/best-ai-assistant-for" className="text-[var(--bronze)]">
              Best AI Assistant For →
            </Link>
          </div>
        </section>
      </main>
    </div>
  )
}
