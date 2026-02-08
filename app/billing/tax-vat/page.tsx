import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Tax & VAT",
  "Manage tax settings, VAT IDs, and regional billing compliance.",
  "/billing/tax-vat"
)

export default function BillingTaxVatPage() {
  return (
    <PageShell
      title="Tax & VAT"
      subtitle="Manage tax settings, VAT IDs, and regional billing compliance."
      breadcrumb={{ name: "Tax & VAT", path: "/billing/tax-vat" }}
      sections={[
        {
          title: "Tax Configuration",
          items: [
            "VAT/GST ID capture with validation.",
            "Regional tax rules by billing country.",
            "Invoice tax line item breakdowns.",
          ],
        },
        {
          title: "Compliance Records",
          items: [
            "Store exemption certificates and supporting docs.",
            "Audit-ready documentation export.",
            "Local tax rates applied automatically.",
          ],
        },
      ]}
      ctaLabel="Payment Methods"
      ctaHref="/billing/payment-methods"
    />
  )
}
