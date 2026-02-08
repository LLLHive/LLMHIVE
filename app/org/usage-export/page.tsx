import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Usage Export",
  "Export usage data for finance, analytics, and compliance.",
  "/org/usage-export"
)

export default function OrgUsageExportPage() {
  return (
    <PageShell
      title="Usage Export"
      subtitle="Export usage data for finance, analytics, and compliance."
      breadcrumb={{ name: "Usage Export", path: "/org/usage-export" }}
      sections={[
        {
          title: "Export Options",
          items: [
            "CSV and JSON exports by time range.",
            "Scheduled delivery to data warehouses.",
            "Per-team and per-project segmentation.",
          ],
        },
        {
          title: "Compliance Support",
          items: [
            "Audit-ready records with timestamps.",
            "User attribution and workspace IDs.",
            "Retention policies by plan.",
          ],
        },
      ]}
      ctaLabel="Usage Dashboard"
      ctaHref="/usage"
    />
  )
}
