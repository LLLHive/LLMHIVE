import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Slack Integration",
  "Deliver alerts and insights directly to your team’s Slack channels.",
  "/integrations/slack"
)

export default function IntegrationsSlackPage() {
  return (
    <PageShell
      title="Slack Integration"
      subtitle="Deliver alerts and insights directly to your team’s Slack channels."
      breadcrumb={{ name: "Slack Integration", path: "/integrations/slack" }}
      sections={[
        {
          title: "Alerting",
          items: [
            "Benchmark completion notifications.",
            "Usage threshold alerts and spend warnings.",
            "Incident updates for on-call teams.",
          ],
        },
        {
          title: "Collaboration",
          items: [
            "Share orchestration summaries with stakeholders.",
            "Quick links to analytics dashboards.",
            "Route support requests from Slack to tickets.",
          ],
        },
      ]}
      ctaLabel="Integrations Hub"
      ctaHref="/integrations"
    />
  )
}
