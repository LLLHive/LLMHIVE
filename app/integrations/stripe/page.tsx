import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Stripe Integration",
  "Connect billing, invoices, and subscription status with Stripe.",
  "/integrations/stripe"
)

export default function IntegrationsStripePage() {
  return (
    <PageShell
      title="Stripe Integration"
      subtitle="Connect billing, invoices, and subscription status with Stripe."
      breadcrumb={{ name: "Stripe Integration", path: "/integrations/stripe" }}
      sections={[
        {
          title: "Subscription Sync",
          items: [
            "Real-time plan status updates.",
            "Invoice and payment reconciliation.",
            "Usage metadata forwarded to Stripe.",
          ],
        },
        {
          title: "Revenue Operations",
          items: [
            "Automated dunning workflows.",
            "Revenue reporting by tier.",
            "Support for multi-currency payments.",
          ],
        },
      ]}
      ctaLabel="Integrations Hub"
      ctaHref="/integrations"
    />
  )
}
