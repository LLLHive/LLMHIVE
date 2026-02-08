import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Upgrade Flow",
  "Move to the right plan with clear usage forecasts and billing alignment.",
  "/pricing/upgrade"
)

export default function PricingUpgradePage() {
  return (
    <PageShell
      title="Upgrade Flow"
      subtitle="Move to the right plan with clear usage forecasts and billing alignment."
      breadcrumb={{ name: "Upgrade Flow", path: "/pricing/upgrade" }}
      sections={[
        {
          title: "Upgrade Options",
          items: [
            "Recommended plan based on usage trends.",
            "Immediate access to higher ELITE quotas.",
            "Pro-rated billing adjustments.",
          ],
        },
        {
          title: "Decision Support",
          items: [
            "Cost vs quality tradeoff analysis.",
            "Team seat management with approval flows.",
            "Enterprise procurement support.",
          ],
        },
      ]}
      ctaLabel="Compare Plans"
      ctaHref="/pricing/compare"
    />
  )
}
