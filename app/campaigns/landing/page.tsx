import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Campaign Landing Pages",
  "Manage and publish campaign-specific landing pages with tracking.",
  "/campaigns/landing"
)

export default function CampaignLandingPage() {
  return (
    <PageShell
      title="Campaign Landing Pages"
      subtitle="Manage and publish campaign-specific landing pages with tracking."
      breadcrumb={{ name: "Campaign Landing Pages", path: "/campaigns/landing" }}
      sections={[
        {
          title: "Campaign Setup",
          items: [
            "Create landing pages tied to specific offers.",
            "Enable A/B testing for messaging.",
            "Capture lead information with forms.",
          ],
        },
        {
          title: "Performance Tracking",
          items: [
            "Conversion rate analytics per campaign.",
            "Attribution based on source and medium.",
            "Export campaign performance reports.",
          ],
        },
      ]}
      ctaLabel="UTM Tracking"
      ctaHref="/utm"
    />
  )
}
