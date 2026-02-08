import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Integrations Hub",
  "Connect LLMHive to your finance, CRM, and collaboration stack.",
  "/integrations"
)

export default function IntegrationsPage() {
  return (
    <PageShell
      title="Integrations Hub"
      subtitle="Connect LLMHive to your finance, CRM, and collaboration stack."
      breadcrumb={{ name: "Integrations Hub", path: "/integrations" }}
      sections={[
        {
          title: "Core Integrations",
          items: [
            "QuickBooks for finance workflows.",
            "Stripe for subscription and payment signals.",
            "CRM connectors for HubSpot and Salesforce.",
          ],
        },
        {
          title: "Automation",
          items: [
            "Sync usage data and billing updates.",
            "Trigger workflows from benchmark results.",
            "Webhook support for custom integrations.",
          ],
        },
      ]}
      ctaLabel="Request Integration"
      ctaHref="/contact"
    />
  )
}
