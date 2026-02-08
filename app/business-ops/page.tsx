import Link from "next/link"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Business Ops Hub",
  "Central navigation for trust, revenue, operations, support, and integrations.",
  "/business-ops"
)

const sections = [
  {
    title: "Business & Trust",
    description: "Security, compliance, and governance resources.",
    links: [
      { label: "Security", href: "/security" },
      { label: "Compliance", href: "/compliance" },
      { label: "Status", href: "/status" },
      { label: "SLA", href: "/sla" },
      { label: "Responsible AI", href: "/responsible-ai" },
      { label: "DPA", href: "/dpa" },
    ],
  },
  {
    title: "Customer & Revenue",
    description: "Usage, billing, and pricing operations.",
    links: [
      { label: "Usage Dashboard", href: "/usage" },
      { label: "Usage Limits", href: "/usage/limits" },
      { label: "Overage Policy", href: "/usage/overage-policy" },
      { label: "Billing History", href: "/billing/history" },
      { label: "Invoices", href: "/billing/invoices" },
      { label: "Tax & VAT", href: "/billing/tax-vat" },
      { label: "Payment Methods", href: "/billing/payment-methods" },
      { label: "Plan Comparison", href: "/pricing/compare" },
      { label: "Upgrade Flow", href: "/pricing/upgrade" },
    ],
  },
  {
    title: "Org Management",
    description: "Access control and operational governance.",
    links: [
      { label: "Teams", href: "/org/teams" },
      { label: "Roles & Permissions", href: "/org/roles" },
      { label: "SSO & SAML", href: "/org/sso" },
      { label: "Audit Logs", href: "/org/audit-logs" },
      { label: "API Keys", href: "/org/api-keys" },
      { label: "Webhooks", href: "/org/webhooks" },
      { label: "Usage Export", href: "/org/usage-export" },
    ],
  },
  {
    title: "Support & Knowledge",
    description: "Self-service and assisted support resources.",
    links: [
      { label: "Docs", href: "/docs" },
      { label: "Guides", href: "/guides" },
      { label: "API Reference", href: "/api-reference" },
      { label: "Troubleshooting", href: "/troubleshooting" },
      { label: "FAQ", href: "/faq" },
      { label: "Support Portal", href: "/support/portal" },
      { label: "Support Chat", href: "/support/chat" },
    ],
  },
  {
    title: "Marketing",
    description: "GTM and growth resources.",
    links: [
      { label: "Case Studies", href: "/case-studies" },
      { label: "Testimonials", href: "/testimonials" },
      { label: "Competitor Comparisons", href: "/competitors" },
      { label: "ROI Calculator", href: "/roi-calculator" },
      { label: "Email & SMS Preferences", href: "/preferences/notifications" },
      { label: "Campaign Landing Pages", href: "/campaigns/landing" },
      { label: "UTM Tracking", href: "/utm" },
    ],
  },
  {
    title: "Integrations",
    description: "Finance, CRM, and collaboration connectors.",
    links: [
      { label: "Integrations Hub", href: "/integrations" },
      { label: "QuickBooks", href: "/integrations/quickbooks" },
      { label: "Stripe", href: "/integrations/stripe" },
      { label: "CRM (HubSpot/Salesforce)", href: "/integrations/crm" },
      { label: "Slack", href: "/integrations/slack" },
    ],
  },
]

export default function BusinessOpsHubPage() {
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
                    name: "Business Ops Hub",
                    item: "https://www.llmhive.ai/business-ops",
                  },
                ],
              },
            ],
          }),
        }}
      />
      <div className="mx-auto max-w-6xl px-6 py-16">
        <div className="flex items-center justify-between">
          <Link href="/" className="text-sm text-white/60 hover:text-white">
            ← Back to LLMHive
          </Link>
          <Link
            href="/business-ops/navigation"
            className="rounded-full border border-white/20 px-4 py-2 text-sm text-white/80 hover:border-white/60 hover:text-white"
          >
            Full Navigation
          </Link>
        </div>

        <div className="mt-10">
          <h1 className="text-3xl font-semibold tracking-tight md:text-5xl">
            Business Ops Hub
          </h1>
          <p className="mt-4 max-w-3xl text-base text-white/70 md:text-lg">
            Central navigation for trust, revenue, operations, support, and
            integrations. Use this page as the operational dashboard index.
          </p>
        </div>

        <div className="mt-12 grid gap-8 md:grid-cols-2">
          {sections.map((section) => (
            <section
              key={section.title}
              className="rounded-2xl border border-white/10 bg-white/5 p-6"
            >
              <h2 className="text-lg font-semibold">{section.title}</h2>
              <p className="mt-2 text-sm text-white/70">
                {section.description}
              </p>
              <ul className="mt-4 grid gap-2 text-sm text-white/80">
                {section.links.map((link) => (
                  <li key={link.href}>
                    <Link className="hover:text-white" href={link.href}>
                      {link.label}
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
