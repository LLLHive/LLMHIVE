import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Usage Limits",
  "Configure limits and alerts to keep usage predictable and budgeted.",
  "/usage/limits"
)

export default function UsageLimitsPage() {
  return (
    <PageShell
      title="Usage Limits"
      subtitle="Configure limits and alerts to keep usage predictable and budgeted."
      breadcrumb={{ name: "Usage Limits", path: "/usage/limits" }}
      sections={[
        {
          title: "Limit Controls",
          items: [
            "Per-team and per-workspace ELITE caps.",
            "Daily and monthly budget ceilings.",
            "Automatic throttling and notifications.",
          ],
        },
        {
          title: "Governance",
          items: [
            "Approval workflows for limit changes.",
            "Audit trails for limit updates.",
            "Role-based access to controls.",
          ],
        },
      ]}
      ctaLabel="Overage Policy"
      ctaHref="/usage/overage-policy"
    />
  )
}
