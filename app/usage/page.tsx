import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Usage Dashboard",
  "Monitor usage, performance, and spend across all teams and workflows.",
  "/usage"
)

export default function UsageDashboardPage() {
  return (
    <PageShell
      title="Usage Dashboard"
      subtitle="Monitor usage, performance, and spend across all teams and workflows."
      breadcrumb={{ name: "Usage Dashboard", path: "/usage" }}
      sections={[
        {
          title: "Usage Insights",
          items: [
            "ELITE vs FREE query utilization trends.",
            "Model routing distribution and success rates.",
            "Cost per workflow and per team breakdowns.",
          ],
        },
        {
          title: "Controls",
          items: [
            "Budget alerts and usage thresholds.",
            "Export usage data for finance teams.",
            "Scheduled reports for stakeholders.",
          ],
        },
      ]}
      ctaLabel="Usage Limits"
      ctaHref="/usage/limits"
    />
  )
}
