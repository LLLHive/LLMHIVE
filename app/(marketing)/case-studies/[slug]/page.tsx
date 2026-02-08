import { notFound } from "next/navigation"
import type { Metadata } from "next"
import Link from "next/link"
import { caseStudies } from "../content"

type PageProps = {
  params: { slug: string }
}

export function generateStaticParams() {
  return caseStudies.map((item) => ({ slug: item.slug }))
}

export function generateMetadata({ params }: PageProps): Metadata {
  const page = caseStudies.find((item) => item.slug === params.slug)
  if (!page) {
    return { title: "LLMHive" }
  }
  return {
    title: page.title,
    description: page.summary,
    openGraph: {
      title: page.title,
      description: page.summary,
      type: "article",
    },
    twitter: {
      card: "summary_large_image",
      title: page.title,
      description: page.summary,
    },
  }
}

function renderStructuredData(page: (typeof caseStudies)[number]) {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "TechArticle",
        headline: page.title,
        description: page.summary,
        author: {
          "@type": "Organization",
          name: "LLMHive",
        },
        mainEntityOfPage: `https://www.llmhive.ai/case-studies/${page.slug}`,
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
        "@type": "ItemList",
        name: "Case Study Outcomes",
        itemListElement: page.outcomes.map((item, index) => ({
          "@type": "ListItem",
          position: index + 1,
          name: item,
        })),
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "Case Studies",
            item: "https://www.llmhive.ai/case-studies",
          },
          {
            "@type": "ListItem",
            position: 2,
            name: page.title,
            item: `https://www.llmhive.ai/case-studies/${page.slug}`,
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

export default function CaseStudyPage({ params }: PageProps) {
  const page = caseStudies.find((item) => item.slug === params.slug)
  if (!page) {
    notFound()
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      {renderStructuredData(page)}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <p className="text-sm text-muted-foreground">{page.industry} Case Study</p>
          <h1 className="text-3xl md:text-4xl font-bold">{page.title}</h1>
          <p className="mt-2 text-muted-foreground">{page.summary}</p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-12 space-y-10">
        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Challenge</h2>
          <p className="mt-3 text-sm text-muted-foreground leading-relaxed">{page.challenge}</p>
        </section>

        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">LLMHive Solution</h2>
          <p className="mt-3 text-sm text-muted-foreground leading-relaxed">{page.solution}</p>
          <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
            {page.highlights.map((item) => (
              <li key={item}>• {item}</li>
            ))}
          </ul>
        </section>

        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Outcomes</h2>
          <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
            {page.outcomes.map((item) => (
              <li key={item}>• {item}</li>
            ))}
          </ul>
        </section>

        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Impact Metrics</h2>
          <div className="mt-4 grid gap-3 md:grid-cols-3">
            {page.metrics.map((item) => (
              <div key={item} className="rounded-xl border border-border/50 bg-background/40 p-4">
                <p className="text-sm font-semibold text-foreground">{item}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Implementation Timeline</h2>
          <ol className="mt-4 space-y-2 text-sm text-muted-foreground">
            {page.timeline.map((item) => (
              <li key={item}>• {item}</li>
            ))}
          </ol>
        </section>

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
            Explore related comparisons and industry guidance.
          </p>
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <Link href="/comparisons" className="text-[var(--bronze)]">
              Comparisons →
            </Link>
            <Link href={`/industries/${page.industry.toLowerCase()}`} className="text-[var(--bronze)]">
              {page.industry} FAQs →
            </Link>
            <Link href="/use-cases" className="text-[var(--bronze)]">
              Use Cases →
            </Link>
          </div>
        </section>
      </main>
    </div>
  )
}
