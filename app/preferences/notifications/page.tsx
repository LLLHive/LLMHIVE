import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Email & SMS Preferences",
  "Control communications for alerts, marketing, and system updates.",
  "/preferences/notifications"
)

export default function NotificationsPreferencesPage() {
  return (
    <PageShell
      title="Email & SMS Preferences"
      subtitle="Control communications for alerts, marketing, and system updates."
      breadcrumb={{ name: "Email & SMS Preferences", path: "/preferences/notifications" }}
      sections={[
        {
          title: "Notification Types",
          items: [
            "Usage and budget alerts.",
            "Product updates and releases.",
            "Marketing campaigns and promotions.",
          ],
        },
        {
          title: "Compliance",
          items: [
            "Opt-in and opt-out controls by channel.",
            "Regional compliance and consent tracking.",
            "Audit logs for preference changes.",
          ],
        },
      ]}
      ctaLabel="Support Portal"
      ctaHref="/support/portal"
    />
  )
}
