import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Plan Comparison",
  "Compare features, limits, and support levels across LLMHive plans.",
  "/pricing/compare"
)

export default function PricingComparePage() {
  return (
    <PageShell
      title="Plan Comparison"
      subtitle="Compare features, limits, and support levels across LLMHive plans."
      breadcrumb={{ name: "Plan Comparison", path: "/pricing/compare" }}
      sections={[
        {
          title: "Feature Highlights",
          items: [
            "ELITE query quotas and unlimited FREE usage.",
            "Memory retention differences by plan.",
            "Support SLAs and response times.",
          ],
        },
        {
          title: "Enterprise Readiness",
          items: [
            "SSO/SAML and audit logging.",
            "Compliance documentation support.",
            "Dedicated technical account management.",
          ],
        },
      ]}
      ctaLabel="Upgrade Plans"
      ctaHref="/pricing/upgrade"
    />
  )
}
