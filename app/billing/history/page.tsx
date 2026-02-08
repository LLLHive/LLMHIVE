import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Billing History",
  "Track billing cycles, receipts, and usage summaries across all subscriptions.",
  "/billing/history"
)

export default function BillingHistoryPage() {
  return (
    <PageShell
      title="Billing History"
      subtitle="Track billing cycles, receipts, and usage summaries across all subscriptions."
      breadcrumb={{ name: "Billing History", path: "/billing/history" }}
      sections={[
        {
          title: "History Overview",
          items: [
            "Monthly billing summaries with ELITE usage totals.",
            "Downloadable receipts and payment confirmations.",
            "Filter by workspace, team, or cost center.",
          ],
        },
        {
          title: "Audit Ready",
          items: [
            "Immutable billing logs for compliance.",
            "Exportable statements for finance teams.",
            "Clear reconciliation with usage dashboards.",
          ],
        },
      ]}
      ctaLabel="View Invoices"
      ctaHref="/billing/invoices"
    />
  )
}
