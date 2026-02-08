import PageShell from "@/components/business/PageShell"
import { buildBusinessMetadata } from "@/components/business/metadata"

export const metadata = buildBusinessMetadata(
  "Support Chat",
  "Real-time assistance from LLMHive support and solution engineers.",
  "/support/chat"
)

export default function SupportChatPage() {
  return (
    <PageShell
      title="Support Chat"
      subtitle="Real-time assistance from LLMHive support and solution engineers."
      breadcrumb={{ name: "Support Chat", path: "/support/chat" }}
      sections={[
        {
          title: "Live Support",
          items: [
            "Chat with support during business hours.",
            "Priority routing for enterprise plans.",
            "Share logs and request IDs in chat.",
          ],
        },
        {
          title: "Response Commitments",
          items: [
            "Guaranteed response SLAs for critical incidents.",
            "Escalation to on-call engineering.",
            "Post-resolution summaries provided.",
          ],
        },
      ]}
      ctaLabel="Support Portal"
      ctaHref="/support/portal"
    />
  )
}
