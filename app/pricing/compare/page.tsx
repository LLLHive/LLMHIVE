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
            "Spend-guarded elite orchestration for paid plans.",
            "90-day conversation memory on Standard and Premium.",
            "Automatic multi-model routing on Standard and Premium.",
            "Single flagship model pick on Enterprise — choose one frontier model per request.",
            "Enterprise support and team controls.",
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
