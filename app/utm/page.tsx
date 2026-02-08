import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "UTM Tracking",
  "Standardize campaign tagging and ensure accurate attribution.",
  "/utm"
)

export default function UtmTrackingPage() {
  return (
    <PageShell
      title="UTM Tracking"
      subtitle="Standardize campaign tagging and ensure accurate attribution."
      breadcrumb={{ name: "UTM Tracking", path: "/utm" }}
      sections={[
        {
          title: "UTM Governance",
          items: [
            "Controlled taxonomy for source, medium, and campaign.",
            "Auto-validation for consistent naming.",
            "Centralized tracking across channels.",
          ],
        },
        {
          title: "Reporting",
          items: [
            "Attribution reporting by campaign.",
            "Cross-channel ROI visibility.",
            "Exportable campaign logs.",
          ],
        },
      ]}
      ctaLabel="Campaign Landing"
      ctaHref="/campaigns/landing"
    />
  )
}
