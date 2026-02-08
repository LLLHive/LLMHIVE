import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Support Portal",
  "Centralized support for tickets, incident updates, and account help.",
  "/support/portal"
)

export default function SupportPortalPage() {
  return (
    <PageShell
      title="Support Portal"
      subtitle="Centralized support for tickets, incident updates, and account help."
      breadcrumb={{ name: "Support Portal", path: "/support/portal" }}
      sections={[
        {
          title: "Support Coverage",
          items: [
            "Ticket intake with priority routing.",
            "Incident updates and historical timelines.",
            "Dedicated enterprise escalation paths.",
          ],
        },
        {
          title: "Self-Service",
          items: [
            "Knowledge base links and troubleshooting guides.",
            "Account configuration checklists.",
            "Billing and invoice support workflows.",
          ],
        },
      ]}
      ctaLabel="Open Support Ticket"
      ctaHref="/support/tickets"
    />
  )
}
