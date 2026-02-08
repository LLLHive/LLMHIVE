import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Audit Logs",
  "Track every critical action across accounts and workspaces.",
  "/org/audit-logs"
)

export default function OrgAuditLogsPage() {
  return (
    <PageShell
      title="Audit Logs"
      subtitle="Track every critical action across accounts and workspaces."
      breadcrumb={{ name: "Audit Logs", path: "/org/audit-logs" }}
      sections={[
        {
          title: "Log Coverage",
          items: [
            "Authentication and permission changes.",
            "Billing, usage, and integration updates.",
            "Model routing policy adjustments.",
          ],
        },
        {
          title: "Export & Retention",
          items: [
            "Configurable retention periods.",
            "Export logs for compliance audits.",
            "Webhook-based real-time streaming.",
          ],
        },
      ]}
      ctaLabel="API Keys"
      ctaHref="/org/api-keys"
    />
  )
}
