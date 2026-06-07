import Link from "next/link"
import type { Metadata } from "next"
import { Button } from "@/components/ui/button"
import { ArrowLeft } from "lucide-react"
import { sitePath } from "@/lib/site-url"

export const metadata: Metadata = {
  title: "Privacy Policy - LLMHive",
  description: "Read the LLMHive privacy policy and data protection practices.",
  alternates: {
    canonical: sitePath('/privacy'),
  },
  openGraph: {
    title: "LLMHive Privacy Policy",
    description: "Read the LLMHive privacy policy and data protection practices.",
    type: "article",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive Privacy Policy",
    description: "Read the LLMHive privacy policy and data protection practices.",
  },
}

function renderStructuredData() {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "Privacy Policy",
            item: sitePath('/privacy'),
          },
        ],
      },
    ],
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
    />
  )
}

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-background">
      {renderStructuredData()}
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
          <Button variant="ghost" size="sm" className="gap-2" asChild>
            <Link href="/">
              <ArrowLeft className="h-4 w-4" />
              Back to Home
            </Link>
          </Button>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-12">
        <h1 className="text-4xl font-bold mb-2">Privacy Policy</h1>
        <p className="text-muted-foreground mb-8">Last updated: May 7, 2026</p>

        <div className="prose prose-invert max-w-none space-y-8">
          <section>
            <h2 className="text-2xl font-semibold mb-4">1. Introduction</h2>
            <p className="text-muted-foreground leading-relaxed">
              LLMHive (&quot;we&quot;, &quot;our&quot;, or &quot;us&quot;) is committed to protecting your privacy. 
              This Privacy Policy explains how we collect, use, disclose, and safeguard your 
              information when you use our AI orchestration platform.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">2. Information We Collect</h2>
            <h3 className="text-lg font-medium mb-2">2.1 Information You Provide</h3>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>Account information (email, name) when you sign up</li>
              <li>Payment information processed securely through Stripe</li>
              <li>Chat conversations and prompts you submit to our AI services</li>
              <li>Feedback and support communications</li>
            </ul>

            <h3 className="text-lg font-medium mb-2 mt-4">2.2 Automatically Collected Information</h3>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>Usage data (features used, time spent)</li>
              <li>Device information (browser type, OS)</li>
              <li>Log data (IP address, access times)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">3. How We Use Your Information</h2>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>To provide and improve our AI orchestration services</li>
              <li>To process payments and manage subscriptions</li>
              <li>To communicate with you about your account</li>
              <li>To analyze usage patterns and improve our platform</li>
              <li>To ensure security and prevent fraud</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">4. Data Retention</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              We retain personal data only as long as needed to provide the Service and to meet
              legal, accounting, and security obligations. Specifically:
            </p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li><strong>Conversation memory:</strong> Up to 90 days, after which entries are eligible for deletion. You may delete conversations at any time, or enable Incognito Mode to disable storage.</li>
              <li><strong>Account data:</strong> Retained for the lifetime of the account; deleted within 30 days of account closure unless retention is required by law (e.g., tax records).</li>
              <li><strong>Payment records:</strong> Retained by Stripe and by us for at least 7 years to satisfy financial-record requirements.</li>
              <li><strong>Server and security logs:</strong> Retained for up to 90 days for incident investigation and abuse prevention.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">5. Data Security</h2>
            <p className="text-muted-foreground leading-relaxed">
              We implement industry-standard security measures including encryption in transit (TLS),
              encryption at rest for stored data, scoped access controls, and regular security review.
              Production secrets are managed in Google Secret Manager and never exposed to client
              code. We do not sell personal data.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">6. Third-Party Services and Data Sharing</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              To deliver the Service we share specific data with the following processors. Each
              acts only on our instructions and only for the purposes listed.
            </p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>
                <strong>AI providers (OpenAI, Anthropic, Google, DeepSeek, xAI, Together, OpenRouter):</strong>{" "}
                Your prompts and conversation context are sent to one or more of these providers to generate
                responses. We do not opt your prompts into provider training where the provider offers an
                opt-out, and we use the API/enterprise endpoints that exclude training on inputs by default
                where available. Provider responses are stored in your account history subject to Section 4.
              </li>
              <li>
                <strong>Authentication (Clerk):</strong> Email, name, and authentication metadata are stored
                in Clerk so we can verify your identity at sign-in. Clerk acts as a data processor under our
                instructions.
              </li>
              <li>
                <strong>Payments (Stripe):</strong> Stripe processes your payment method and stores billing
                details. We never see or store full card numbers. We receive a Stripe customer ID, subscription
                status, and high-level billing events (renewal, cancel, failed payment) and store those in
                Firestore to manage your access.
              </li>
              <li>
                <strong>Hosting (Google Cloud, Vercel):</strong> Application data, including conversation
                memory and subscription status, is stored in Google Cloud (Firestore, US multi-region by
                default). The web frontend is served by Vercel.
              </li>
              <li>
                <strong>Error monitoring and analytics:</strong> If enabled, we use Sentry for error
                monitoring and a privacy-respecting product analytics tool (PostHog or Plausible) to measure
                feature usage. We do not send conversation contents to either; only feature events and error
                metadata.
              </li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">7. International Transfers</h2>
            <p className="text-muted-foreground leading-relaxed">
              Our processors are predominantly located in the United States. If you access the Service
              from the European Economic Area, the United Kingdom, or another jurisdiction, your data
              may be transferred to and processed in the United States. We rely on Standard Contractual
              Clauses (or equivalent) with our processors where required.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">8. Your Rights</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Depending on your location (including under GDPR and CCPA/CPRA), you may have the
              following rights with respect to your personal data:
            </p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>Access a copy of the personal data we hold about you</li>
              <li>Correct inaccurate or incomplete data</li>
              <li>Delete your data (the &quot;right to erasure&quot;), subject to legal retention</li>
              <li>Export your data in a machine-readable format (data portability)</li>
              <li>Object to or restrict certain processing</li>
              <li>Opt out of the sale or sharing of personal data (we do not sell personal data)</li>
              <li>Withdraw consent for any processing that relies on consent</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mt-4">
              To exercise any of these rights, email <strong>info@llmhive.ai</strong>. We will respond
              within 30 days. You also have the right to lodge a complaint with your local data
              protection authority.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">9. Children&apos;s Privacy</h2>
            <p className="text-muted-foreground leading-relaxed">
              The Service is not directed to children under 18. We do not knowingly collect personal
              data from children. If you believe a child has provided us personal data, contact us so
              we can delete it.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">10. Changes to This Policy</h2>
            <p className="text-muted-foreground leading-relaxed">
              We may update this Privacy Policy from time to time. Material changes will be communicated
              by email or in-app notice at least 15 days before they take effect. The &ldquo;Last updated&rdquo;
              date at the top reflects the most recent revision.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">11. Contact Us</h2>
            <p className="text-muted-foreground leading-relaxed">
              If you have questions about this Privacy Policy or your data, contact us at:
              <br /><br />
              <strong>Email:</strong> info@llmhive.ai
            </p>
          </section>
        </div>
      </main>
      <footer className="border-t border-border/60 py-6">
        <div className="max-w-4xl mx-auto px-4 flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
          <Link href="/privacy" className="hover:text-foreground">Privacy</Link>
          <Link href="/terms" className="hover:text-foreground">Terms</Link>
          <Link href="/cookies" className="hover:text-foreground">Cookies</Link>
          <Link href="/contact" className="hover:text-foreground">Contact</Link>
        </div>
      </footer>
    </div>
  )
}

