import Link from "next/link"
import { buildBusinessMetadata } from "@/components/business/metadata"
import { businessPages } from "@/app/(business)/content"

export const metadata = buildBusinessMetadata(
  "Business Ops Navigation",
  "Complete list of operational pages for LLMHive business management.",
  "/business-ops/navigation"
)

const groupedRoutes = [
  {
    title: "Business & Trust",
    routes: [
      "/security",
      "/compliance",
      "/status",
      "/sla",
      "/changelog",
      "/roadmap",
      "/press-kit",
      "/responsible-ai",
      "/dpa",
    ],
  },
  {
    title: "Customer & Revenue",
    routes: [
      "/usage",
      "/billing/history",
      "/billing/invoices",
      "/billing/tax-vat",
      "/billing/payment-methods",
      "/pricing/compare",
      "/pricing/upgrade",
      "/usage/limits",
      "/usage/overage-policy",
    ],
  },
  {
    title: "Org Management",
    routes: [
      "/org/teams",
      "/org/roles",
      "/org/sso",
      "/org/audit-logs",
      "/org/api-keys",
      "/org/webhooks",
      "/org/usage-export",
    ],
  },
  {
    title: "Support & Knowledge",
    routes: [
      "/docs",
      "/guides",
      "/api-reference",
      "/troubleshooting",
      "/faq",
      "/support/portal",
      "/support/chat",
    ],
  },
  {
    title: "Marketing",
    routes: [
      "/case-studies",
      "/testimonials",
      "/competitors",
      "/roi-calculator",
      "/preferences/notifications",
      "/campaigns/landing",
      "/utm",
    ],
  },
  {
    title: "Integrations",
    routes: [
      "/integrations",
      "/integrations/quickbooks",
      "/integrations/stripe",
      "/integrations/crm",
      "/integrations/slack",
    ],
  },
]

const businessPageTitles = Object.entries(businessPages).reduce(
  (acc, [slug, page]) => {
    acc[`/${slug}`] = page.title
    return acc
  },
  {} as Record<string, string>
)

export default function BusinessOpsNavigationPage() {
  return (
    <main className="min-h-screen bg-black text-white">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@graph": [
              {
                "@type": "BreadcrumbList",
                itemListElement: [
                  {
                    "@type": "ListItem",
                    position: 1,
                    name: "Business Ops Navigation",
                    item: "https://www.llmhive.ai/business-ops/navigation",
                  },
                ],
              },
            ],
          }),
        }}
      />
      <div className="mx-auto max-w-5xl px-6 py-16">
        <div className="flex items-center justify-between">
          <Link href="/business-ops" className="text-sm text-white/60 hover:text-white">
            ← Back to Hub
          </Link>
          <Link href="/" className="text-sm text-white/60 hover:text-white">
            Home
          </Link>
        </div>

        <div className="mt-10">
          <h1 className="text-3xl font-semibold tracking-tight md:text-5xl">
            Business Ops Navigation
          </h1>
          <p className="mt-4 text-base text-white/70 md:text-lg">
            Complete list of operational pages for LLMHive business management.
          </p>
        </div>

        <div className="mt-12 space-y-8">
          {groupedRoutes.map((group) => (
            <section
              key={group.title}
              className="rounded-2xl border border-white/10 bg-white/5 p-6"
            >
              <h2 className="text-lg font-semibold">{group.title}</h2>
              <ul className="mt-4 grid gap-2 text-sm text-white/80 md:grid-cols-2">
                {group.routes.map((route) => (
                  <li key={route}>
                    <Link className="hover:text-white" href={route}>
                      {businessPageTitles[route] ?? route}
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </div>
    </main>
  )
}
