import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "SSO & SAML",
  "Enterprise single sign-on with centralized identity management.",
  "/org/sso"
)

export default function OrgSSOPage() {
  return (
    <PageShell
      title="SSO & SAML"
      subtitle="Enterprise single sign-on with centralized identity management."
      breadcrumb={{ name: "SSO & SAML", path: "/org/sso" }}
      sections={[
        {
          title: "SSO Configuration",
          items: [
            "SAML 2.0 identity provider setup.",
            "SCIM provisioning and deprovisioning.",
            "Domain verification and access policies.",
          ],
        },
        {
          title: "Security Controls",
          items: [
            "Enforce MFA for privileged accounts.",
            "Session duration and re-authentication policies.",
            "Audit logs for SSO events.",
          ],
        },
      ]}
      ctaLabel="Audit Logs"
      ctaHref="/org/audit-logs"
    />
  )
}
