import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Webhooks",
  "Automate workflows with real-time event notifications.",
  "/org/webhooks"
)

export default function OrgWebhooksPage() {
  return (
    <PageShell
      title="Webhooks"
      subtitle="Automate workflows with real-time event notifications."
      breadcrumb={{ name: "Webhooks", path: "/org/webhooks" }}
      sections={[
        {
          title: "Event Types",
          items: [
            "Usage thresholds and budget alerts.",
            "Benchmark completion and status events.",
            "Billing updates and invoice availability.",
          ],
        },
        {
          title: "Reliability",
          items: [
            "Retry policies with exponential backoff.",
            "Signature verification for secure delivery.",
            "Dead-letter queue export options.",
          ],
        },
      ]}
      ctaLabel="Usage Export"
      ctaHref="/org/usage-export"
    />
  )
}
