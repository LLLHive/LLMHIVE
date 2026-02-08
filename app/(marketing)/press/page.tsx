import Link from "next/link"
import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Press & Media Kit - LLMHive",
  description:
    "Official LLMHive press release, media kit, and assets for journalists, bloggers, and influencers.",
  alternates: {
    canonical: "https://www.llmhive.ai/press",
  },
  openGraph: {
    title: "LLMHive Press & Media Kit",
    description:
      "Download the LLMHive press release, media kit, and official assets.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive Press & Media Kit",
    description:
      "Download the LLMHive press release, media kit, and official assets.",
  },
}

const assets = [
  {
    name: "Press Release (Long)",
    description: "Full 600–800 word press release in plain text.",
    href: "/press/press-release-long",
  },
  {
    name: "Press Release (Wire)",
    description: "Condensed 400–500 word wire release in plain text.",
    href: "/press/press-release-wire",
  },
  {
    name: "Fact Sheet",
    description: "One-page summary of LLMHive’s mission and results.",
    href: "/press/fact-sheet",
  },
  {
    name: "Media Kit",
    description: "Official company facts, links, and brand assets in JSON.",
    href: "/press/media-kit",
  },
]

function renderStructuredData() {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "ItemList",
        name: "Press Assets",
        itemListElement: assets.map((asset, index) => ({
          "@type": "ListItem",
          position: index + 1,
          name: asset.name,
          url: `https://www.llmhive.ai${asset.href}`,
        })),
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "Press",
            item: "https://www.llmhive.ai/press",
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

export default function PressPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {renderStructuredData()}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <p className="text-xs uppercase tracking-[0.3em] text-muted-foreground">
            Press & Media
          </p>
          <h1 className="text-3xl md:text-4xl font-bold">LLMHive Press Room</h1>
          <p className="mt-2 text-muted-foreground">
            Official press release, media kit, and brand assets for editors and creators.
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-12">
        <section className="rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Quick Links</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Use these official assets for coverage, stories, and press listings.
          </p>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            {assets.map((asset) => (
              <div key={asset.name} className="rounded-xl border border-border/60 bg-background/60 p-4">
                <h3 className="text-base font-semibold">{asset.name}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{asset.description}</p>
                <Link
                  href={asset.href}
                  className="mt-3 inline-flex text-sm text-[var(--bronze)]"
                >
                  Download →
                </Link>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-10 rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Core Company Links</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Reference these official URLs for backlinks and citations.
          </p>
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <Link href="/landing" className="text-[var(--bronze)]">
              Product Overview →
            </Link>
            <Link href="/orchestration" className="text-[var(--bronze)]">
              Orchestration →
            </Link>
            <Link href="/models" className="text-[var(--bronze)]">
              Models →
            </Link>
            <Link href="/case-studies" className="text-[var(--bronze)]">
              Case Studies →
            </Link>
            <Link href="/comparisons" className="text-[var(--bronze)]">
              Comparisons →
            </Link>
            <Link href="/demo" className="text-[var(--bronze)]">
              Demo →
            </Link>
            <Link href="/contact" className="text-[var(--bronze)]">
              Media Contact →
            </Link>
          </div>
        </section>

        <section className="mt-10 rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Press Notes</h2>
          <ul className="mt-3 space-y-2 text-sm text-muted-foreground">
            <li>Benchmark claims are reported by LLMHive and available on request.</li>
            <li>For interviews or additional assets, contact press@llmhive.ai.</li>
            <li>Logo usage: use official assets without color alterations.</li>
          </ul>
        </section>
      </main>
    </div>
  )
}
