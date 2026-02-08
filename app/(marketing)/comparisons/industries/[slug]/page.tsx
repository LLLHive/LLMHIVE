import { notFound } from "next/navigation"
import type { Metadata } from "next"
import Link from "next/link"
import { industryRoles } from "../content"
import { industryToolComparisons } from "../tools"

type PageProps = {
  params: { slug: string }
}

export function generateStaticParams() {
  return industryRoles.map((item) => ({ slug: item.slug }))
}

export function generateMetadata({ params }: PageProps): Metadata {
  const page = industryRoles.find((item) => item.slug === params.slug)
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

function renderStructuredData(page: (typeof industryRoles)[number]) {
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
        mainEntityOfPage: `https://www.llmhive.ai/comparisons/industries/${page.slug}`,
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
            name: "Comparisons",
            item: "https://www.llmhive.ai/comparisons",
          },
          {
            "@type": "ListItem",
            position: 2,
            name: "Industry Comparisons",
            item: "https://www.llmhive.ai/comparisons/industries",
          },
          {
            "@type": "ListItem",
            position: 3,
            name: page.title,
            item: `https://www.llmhive.ai/comparisons/industries/${page.slug}`,
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

export default function IndustryRolePage({ params }: PageProps) {
  const page = industryRoles.find((item) => item.slug === params.slug)
  if (!page) {
    notFound()
  }

  const relatedTools = industryToolComparisons.filter(
    (item) => item.industry === params.slug.replace("-teams", "")
  )

  return (
    <div className="min-h-screen bg-background text-foreground">
      {renderStructuredData(page)}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <p className="text-sm text-muted-foreground">Industry Guide</p>
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
          <h2 className="text-xl font-semibold">Why LLMHive</h2>
          <ul className="mt-4 space-y-2 text-sm text-muted-foreground">
            {page.bullets.map((item) => (
              <li key={item}>• {item}</li>
            ))}
          </ul>
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

        {relatedTools.length > 0 && (
          <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
            <h2 className="text-xl font-semibold">Tool Comparisons</h2>
            <p className="mt-2 text-sm text-muted-foreground">
              Explore comparisons with industry-specific tools.
            </p>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {relatedTools.map((item) => (
                <Link
                  key={item.tool}
                  href={`/comparisons/industries/${item.industry}/${item.tool}`}
                  className="rounded-xl border border-border/60 bg-background/40 p-4 transition-all hover:border-[var(--bronze)]/40"
                >
                  <h3 className="text-sm font-semibold">{item.title}</h3>
                  <p className="mt-2 text-xs text-muted-foreground">{item.description}</p>
                </Link>
              ))}
            </div>
          </section>
        )}

        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Next Steps</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Explore related comparisons and role-based guides.
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
