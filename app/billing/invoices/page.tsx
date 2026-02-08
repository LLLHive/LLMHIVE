import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Invoices",
  "Access invoices, tax documentation, and billing records for every plan.",
  "/billing/invoices"
)

export default function BillingInvoicesPage() {
  return (
    <PageShell
      title="Invoices"
      subtitle="Access invoices, tax documentation, and billing records for every plan."
      breadcrumb={{ name: "Invoices", path: "/billing/invoices" }}
      sections={[
        {
          title: "Invoice Access",
          items: [
            "Monthly invoice PDFs with line item detail.",
            "Multi-entity billing support for enterprise orgs.",
            "Export invoices for accounting systems.",
          ],
        },
        {
          title: "Billing Controls",
          items: [
            "Consolidated invoicing across teams.",
            "PO number support and invoice notes.",
            "Automated delivery to finance contacts.",
          ],
        },
      ]}
      ctaLabel="Billing History"
      ctaHref="/billing/history"
    />
  )
}
