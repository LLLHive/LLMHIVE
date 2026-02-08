import Link from "next/link"

type PageSection = {
  title: string
  description?: string
  items?: string[]
}

type PageShellProps = {
  title: string
  subtitle: string
  sections: PageSection[]
  ctaLabel?: string
  ctaHref?: string
  breadcrumb?: {
    name: string
    path: string
  }
}

export default function PageShell({
  title,
  subtitle,
  sections,
  ctaLabel,
  ctaHref,
  breadcrumb,
}: PageShellProps) {
  const breadcrumbStructuredData = breadcrumb
    ? {
        "@context": "https://schema.org",
        "@graph": [
          {
            "@type": "BreadcrumbList",
            itemListElement: [
              {
                "@type": "ListItem",
                position: 1,
                name: breadcrumb.name,
                item: `https://www.llmhive.ai${breadcrumb.path}`,
              },
            ],
          },
        ],
      }
    : null

  return (
    <main className="min-h-screen bg-black text-white">
      {breadcrumbStructuredData ? (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(breadcrumbStructuredData) }}
        />
      ) : null}
      <div className="mx-auto max-w-6xl px-6 py-16">
        <div className="flex items-center justify-between gap-4">
          <Link href="/" className="text-sm text-white/60 hover:text-white">
            ← Back to LLMHive
          </Link>
          {ctaLabel && ctaHref ? (
            <Link
              href={ctaHref}
              className="rounded-full border border-white/20 px-4 py-2 text-sm text-white/80 hover:border-white/60 hover:text-white"
            >
              {ctaLabel}
            </Link>
          ) : null}
        </div>

        <div className="mt-10">
          <h1 className="text-3xl font-semibold tracking-tight md:text-5xl">
            {title}
          </h1>
          <p className="mt-4 max-w-3xl text-base text-white/70 md:text-lg">
            {subtitle}
          </p>
        </div>

        <div className="mt-12 grid gap-8 md:grid-cols-2">
          {sections.map((section) => (
            <section
              key={section.title}
              className="rounded-2xl border border-white/10 bg-white/5 p-6"
            >
              <h2 className="text-lg font-semibold">{section.title}</h2>
              {section.description ? (
                <p className="mt-2 text-sm text-white/70">
                  {section.description}
                </p>
              ) : null}
              {section.items && section.items.length > 0 ? (
                <ul className="mt-4 list-disc space-y-2 pl-5 text-sm text-white/70">
                  {section.items.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : null}
            </section>
          ))}
        </div>
      </div>
    </main>
  )
}
