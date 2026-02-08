import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Overage Policy",
  "Understand how overages are handled and how to keep spend predictable.",
  "/usage/overage-policy"
)

export default function UsageOveragePolicyPage() {
  return (
    <PageShell
      title="Overage Policy"
      subtitle="Understand how overages are handled and how to keep spend predictable."
      breadcrumb={{ name: "Overage Policy", path: "/usage/overage-policy" }}
      sections={[
        {
          title: "Overage Handling",
          items: [
            "Automatic downgrade to FREE tier after ELITE limits.",
            "Optional overage approvals for enterprise plans.",
            "Notifications when approaching thresholds.",
          ],
        },
        {
          title: "Billing Transparency",
          items: [
            "Clear line items on monthly invoices.",
            "Forecasting tools for expected overages.",
            "Configurable alerts for finance teams.",
          ],
        },
      ]}
      ctaLabel="Usage Dashboard"
      ctaHref="/usage"
    />
  )
}
