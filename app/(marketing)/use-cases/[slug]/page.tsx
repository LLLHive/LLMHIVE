import Link from "next/link"
import { notFound } from "next/navigation"
import type { Metadata } from "next"
import { useCases } from "../content"

type PageProps = {
  params: { slug: string }
}

export function generateStaticParams() {
  return useCases.map((item) => ({ slug: item.slug }))
}

export function generateMetadata({ params }: PageProps): Metadata {
  const page = useCases.find((item) => item.slug === params.slug)
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

function renderStructuredData(page: (typeof useCases)[number]) {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "TechArticle",
        headline: page.title,
        description: page.description,
        author: {
          "@type": "Organization",
          name: "LLMHive",
        },
        mainEntityOfPage: `https://www.llmhive.ai/use-cases/${page.slug}`,
      },
      {
        "@type": "FAQPage",
        mainEntity: page.faq.map((item) => ({
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
            name: "Use Cases",
            item: "https://www.llmhive.ai/use-cases",
          },
          {
            "@type": "ListItem",
            position: 2,
            name: page.title,
            item: `https://www.llmhive.ai/use-cases/${page.slug}`,
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

export default function UseCaseDetailPage({ params }: PageProps) {
  const page = useCases.find((item) => item.slug === params.slug)
  if (!page) {
    notFound()
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      {renderStructuredData(page)}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <p className="text-sm text-muted-foreground">Use Case</p>
          <h1 className="text-3xl md:text-4xl font-bold">{page.title}</h1>
          <p className="mt-2 text-muted-foreground">{page.description}</p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-12 space-y-10">
        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Quick Answer</h2>
          <p className="mt-3 text-sm text-muted-foreground leading-relaxed">{page.answer}</p>
        </section>

        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Outcomes</h2>
          <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
            {page.outcomes.map((item) => (
              <li key={item}>• {item}</li>
            ))}
          </ul>
        </section>

        {page.sections.map((section) => (
          <section key={section.title} className="rounded-2xl border border-border/60 bg-card/40 p-6">
            <h2 className="text-xl font-semibold">{section.title}</h2>
            <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
              {section.points.map((point) => (
                <li key={point}>• {point}</li>
              ))}
            </ul>
          </section>
        ))}

        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">FAQ</h2>
          <div className="mt-4 space-y-4">
            {page.faq.map((item) => (
              <div key={item.question}>
                <h3 className="text-sm font-semibold">{item.question}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{item.answer}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Next Steps</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Explore comparisons and role-based guidance.
          </p>
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <Link href="/comparisons" className="text-[var(--bronze)]">
              Comparisons →
            </Link>
            <Link href="/best-ai-assistant-for" className="text-[var(--bronze)]">
              Best AI Assistant For →
            </Link>
            <Link href="/faq" className="text-[var(--bronze)]">
              FAQ →
            </Link>
          </div>
        </section>
      </main>
    </div>
  )
}
