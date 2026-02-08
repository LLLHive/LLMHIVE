import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "QuickBooks Integration",
  "Sync invoices, usage, and revenue signals directly to QuickBooks.",
  "/integrations/quickbooks"
)

export default function IntegrationsQuickBooksPage() {
  return (
    <PageShell
      title="QuickBooks Integration"
      subtitle="Sync invoices, usage, and revenue signals directly to QuickBooks."
      breadcrumb={{ name: "QuickBooks Integration", path: "/integrations/quickbooks" }}
      sections={[
        {
          title: "Finance Automation",
          items: [
            "Auto-sync invoices and billing history.",
            "Tag usage by team and cost center.",
            "Track ELITE overages in QuickBooks.",
          ],
        },
        {
          title: "Controls",
          items: [
            "Approval workflows for payments.",
            "Secure OAuth-based connection.",
            "Audit-ready export logs.",
          ],
        },
      ]}
      ctaLabel="Integrations Hub"
      ctaHref="/integrations"
    />
  )
}
