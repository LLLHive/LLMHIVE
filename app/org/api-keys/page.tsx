import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "API Keys",
  "Manage API credentials, rotation policies, and key usage.",
  "/org/api-keys"
)

export default function OrgApiKeysPage() {
  return (
    <PageShell
      title="API Keys"
      subtitle="Manage API credentials, rotation policies, and key usage."
      breadcrumb={{ name: "API Keys", path: "/org/api-keys" }}
      sections={[
        {
          title: "Key Management",
          items: [
            "Create and revoke keys by workspace.",
            "Scoped permissions for different services.",
            "Rotation reminders and auto-expiration.",
          ],
        },
        {
          title: "Usage Visibility",
          items: [
            "Key-level usage analytics.",
            "Alerting for anomalous usage.",
            "Exportable key activity reports.",
          ],
        },
      ]}
      ctaLabel="Webhooks"
      ctaHref="/org/webhooks"
    />
  )
}
