import Link from "next/link"
import type { Metadata } from "next"
import { Button } from "@/components/ui/button"
import { ArrowLeft } from "lucide-react"

export const metadata: Metadata = {
  title: "Privacy Policy - LLMHive",
  description: "Read the LLMHive privacy policy and data protection practices.",
  alternates: {
    canonical: "https://www.llmhive.ai/privacy",
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
            item: "https://www.llmhive.ai/privacy",
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
          <Link href="/">
            <Button variant="ghost" size="sm" className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              Back to Home
            </Button>
          </Link>
          <Link href="/business-ops">
            <Button variant="outline" size="sm">
              Business Ops
            </Button>
          </Link>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-12">
        <h1 className="text-4xl font-bold mb-2">Privacy Policy</h1>
        <p className="text-muted-foreground mb-8">Last updated: January 7, 2026</p>

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
            <p className="text-muted-foreground leading-relaxed">
              We retain your personal data only for as long as necessary to fulfill the purposes 
              outlined in this policy. Chat history is retained for 90 days by default, or you 
              can enable &quot;Incognito Mode&quot; to prevent storage of conversations.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">5. Data Security</h2>
            <p className="text-muted-foreground leading-relaxed">
              We implement industry-standard security measures including encryption in transit (TLS), 
              secure data storage, and regular security audits. Your API keys and sensitive data 
              are stored using enterprise-grade encryption.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">6. Third-Party Services</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              We use the following third-party services to operate our platform:
            </p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li><strong>AI Providers:</strong> OpenAI, Anthropic, Google, DeepSeek, xAI (for AI responses)</li>
              <li><strong>Authentication:</strong> Clerk (for user authentication)</li>
              <li><strong>Payments:</strong> Stripe (for payment processing)</li>
              <li><strong>Hosting:</strong> Vercel, Google Cloud (for infrastructure)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">7. Your Rights</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Depending on your location, you may have the following rights:
            </p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>Access your personal data</li>
              <li>Correct inaccurate data</li>
              <li>Delete your data (&quot;right to be forgotten&quot;)</li>
              <li>Export your data (data portability)</li>
              <li>Opt out of marketing communications</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">8. Contact Us</h2>
            <p className="text-muted-foreground leading-relaxed">
              If you have questions about this Privacy Policy or your data, contact us at:
              <br /><br />
              <strong>Email:</strong> info@llmhive.ai
              <br />
              <strong>Address:</strong> [Your Business Address]
            </p>
          </section>
        </div>
      </main>
      <footer className="border-t border-border/60 py-6">
        <div className="max-w-4xl mx-auto px-4 flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
          <Link href="/business-ops" className="hover:text-foreground">Business Ops</Link>
          <Link href="/privacy" className="hover:text-foreground">Privacy</Link>
          <Link href="/terms" className="hover:text-foreground">Terms</Link>
          <Link href="/cookies" className="hover:text-foreground">Cookies</Link>
          <Link href="/contact" className="hover:text-foreground">Contact</Link>
        </div>
      </footer>
    </div>
  )
}

