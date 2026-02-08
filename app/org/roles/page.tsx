import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Roles & Permissions",
  "Define access policies for admins, analysts, and operators.",
  "/org/roles"
)

export default function OrgRolesPage() {
  return (
    <PageShell
      title="Roles & Permissions"
      subtitle="Define access policies for admins, analysts, and operators."
      breadcrumb={{ name: "Roles & Permissions", path: "/org/roles" }}
      sections={[
        {
          title: "Role Templates",
          items: [
            "Admin, Billing Admin, Analyst, and Operator roles.",
            "Fine-grained control for sensitive tools.",
            "Custom role definitions for enterprise teams.",
          ],
        },
        {
          title: "Permission Audits",
          items: [
            "Review who has access to ELITE workflows.",
            "Track permission changes in audit logs.",
            "Set approval workflows for privilege escalation.",
          ],
        },
      ]}
      ctaLabel="SSO & SAML"
      ctaHref="/org/sso"
    />
  )
}
