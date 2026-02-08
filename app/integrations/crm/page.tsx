import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "CRM Integrations",
  "Connect LLMHive to HubSpot and Salesforce for revenue alignment.",
  "/integrations/crm"
)

export default function IntegrationsCrmPage() {
  return (
    <PageShell
      title="CRM Integrations"
      subtitle="Connect LLMHive to HubSpot and Salesforce for revenue alignment."
      breadcrumb={{ name: "CRM Integrations", path: "/integrations/crm" }}
      sections={[
        {
          title: "Sales Enablement",
          items: [
            "Sync account health and usage trends.",
            "Share benchmark performance summaries.",
            "Automate renewal risk alerts.",
          ],
        },
        {
          title: "Workflow Automation",
          items: [
            "Create tasks from support signals.",
            "Attach invoices to CRM records.",
            "Segment customers by usage tiers.",
          ],
        },
      ]}
      ctaLabel="Integrations Hub"
      ctaHref="/integrations"
    />
  )
}
