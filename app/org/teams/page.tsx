import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Teams",
  "Organize teams, assign ownership, and manage workspace boundaries.",
  "/org/teams"
)

export default function OrgTeamsPage() {
  return (
    <PageShell
      title="Teams"
      subtitle="Organize teams, assign ownership, and manage workspace boundaries."
      breadcrumb={{ name: "Teams", path: "/org/teams" }}
      sections={[
        {
          title: "Team Structure",
          items: [
            "Define teams by business unit or function.",
            "Assign ownership for budgets and workflows.",
            "Share knowledge base access securely.",
          ],
        },
        {
          title: "Operational Controls",
          items: [
            "Team-level usage limits and alerts.",
            "Role-based access to sensitive features.",
            "Audit-ready team change history.",
          ],
        },
      ]}
      ctaLabel="Manage Roles"
      ctaHref="/org/roles"
    />
  )
}
