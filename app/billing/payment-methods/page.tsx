import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Payment Methods",
  "Securely manage cards, ACH, and invoicing preferences.",
  "/billing/payment-methods"
)

export default function BillingPaymentMethodsPage() {
  return (
    <PageShell
      title="Payment Methods"
      subtitle="Securely manage cards, ACH, and invoicing preferences."
      breadcrumb={{ name: "Payment Methods", path: "/billing/payment-methods" }}
      sections={[
        {
          title: "Payment Options",
          items: [
            "Primary and backup payment methods.",
            "ACH and wire support for enterprise plans.",
            "Auto-pay settings and billing contacts.",
          ],
        },
        {
          title: "Security",
          items: [
            "PCI-compliant tokenized storage.",
            "Multi-factor confirmation for updates.",
            "Role-based access to payment details.",
          ],
        },
      ]}
      ctaLabel="Tax & VAT Settings"
      ctaHref="/billing/tax-vat"
    />
  )
}
