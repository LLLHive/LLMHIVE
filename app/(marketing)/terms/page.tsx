import Link from "next/link"
import type { Metadata } from "next"
import { Button } from "@/components/ui/button"
import { ArrowLeft } from "lucide-react"

export const metadata: Metadata = {
  title: "Terms of Service - LLMHive",
  description: "Review the LLMHive terms of service and acceptable use guidelines.",
  alternates: {
    canonical: "https://llmhive.ai/terms",
  },
  openGraph: {
    title: "LLMHive Terms of Service",
    description: "Review the LLMHive terms of service and acceptable use guidelines.",
    type: "article",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive Terms of Service",
    description: "Review the LLMHive terms of service and acceptable use guidelines.",
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
            name: "Terms of Service",
            item: "https://llmhive.ai/terms",
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

export default function TermsOfServicePage() {
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
        </div>
      </header>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-12">
        <h1 className="text-4xl font-bold mb-2">Terms of Service</h1>
        <p className="text-muted-foreground mb-8">Last updated: May 7, 2026</p>

        <div className="prose prose-invert max-w-none space-y-8">
          <section>
            <h2 className="text-2xl font-semibold mb-4">1. Acceptance of Terms</h2>
            <p className="text-muted-foreground leading-relaxed">
              By accessing or using LLMHive (&quot;the Service&quot;), you agree to be bound by these 
              Terms of Service. If you do not agree to these terms, do not use the Service.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">2. Description of Service</h2>
            <p className="text-muted-foreground leading-relaxed">
              LLMHive is an AI orchestration platform that enables users to interact with 
              multiple large language models through a unified interface. The Service includes 
              multi-model orchestration, consensus-building, and intelligent response synthesis.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">3. User Accounts</h2>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>You must provide accurate information when creating an account</li>
              <li>You are responsible for maintaining the security of your account</li>
              <li>You must be at least 18 years old to use the Service</li>
              <li>One person or entity may not maintain multiple accounts</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">4. Acceptable Use</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              You agree NOT to use the Service to:
            </p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>Generate illegal, harmful, or abusive content</li>
              <li>Harass, threaten, or impersonate others</li>
              <li>Violate intellectual property rights</li>
              <li>Distribute malware or engage in hacking</li>
              <li>Circumvent rate limits or access controls</li>
              <li>Generate content that violates AI provider policies</li>
              <li>Use automated systems to abuse the Service</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">5. Subscription and Payments</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              We offer the following subscription tiers:
            </p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2 mb-4">
              <li><strong>Standard ($10/mo, $100/yr):</strong> Spend-guarded elite orchestration and 90-day conversation memory</li>
              <li><strong>Premium ($20/mo, $200/yr):</strong> Spend-guarded elite orchestration and 90-day conversation memory</li>
              <li><strong>Enterprise (custom):</strong> SSO, dedicated capacity, and compliance options under a separate agreement</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Payment terms:
            </p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>Paid subscriptions are billed in advance on a monthly or annual basis through Stripe</li>
              <li>Annual subscriptions receive approximately 17% discount versus monthly billing</li>
              <li>Subscriptions automatically renew at the end of each billing period until cancelled</li>
              <li>Prices may change with at least 30 days notice; existing prepaid periods are honored at the original price</li>
              <li>Applicable taxes (sales tax, VAT, GST) are calculated by Stripe and added at checkout where required</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">6. Cancellation and Refunds</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              <strong>Cancellation.</strong> You may cancel your subscription at any time from the billing portal in your account settings. Cancellation takes effect at the end of the then-current billing period, and you retain paid access until that date. We will not bill you again for that subscription unless you re-subscribe.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              <strong>Refunds.</strong> Subscription fees are generally non-refundable, including for partial billing periods, unused capacity, or after a renewal has charged. We may, at our sole discretion, issue a prorated refund in cases of (a) duplicate charges, (b) extended Service unavailability that materially impairs use, or (c) clear billing errors. Refund requests must be submitted to <strong>info@llmhive.ai</strong> within 14 days of the charge.
            </p>
            <p className="text-muted-foreground leading-relaxed mb-4">
              <strong>Failed payments.</strong> If a renewal payment fails, we will retry per Stripe&apos;s standard schedule. After repeated failure your subscription will be set to <em>past due</em> and access to paid features will be suspended until billing is restored. You will receive an email notification before access is suspended.
            </p>
            <p className="text-muted-foreground leading-relaxed">
              <strong>Chargebacks.</strong> Initiating a chargeback before contacting us at <strong>info@llmhive.ai</strong> is a violation of these Terms and may result in immediate account termination and forfeiture of any data export window described in Section 10.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">7. Intellectual Property</h2>
            <p className="text-muted-foreground leading-relaxed">
              You retain ownership of content you create using the Service. You grant us a
              limited license to process your content to provide the Service. The Service
              itself, including its design, features, and code, is owned by LLMHive.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">8. AI Output Disclaimer</h2>
            <p className="text-muted-foreground leading-relaxed">
              AI-generated content may contain errors, biases, or inaccuracies. You are
              responsible for reviewing and verifying any AI output before use. The Service
              should not be used as a substitute for professional advice (legal, medical,
              financial, etc.).
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">9. Limitation of Liability</h2>
            <p className="text-muted-foreground leading-relaxed">
              THE SERVICE IS PROVIDED &quot;AS IS&quot; WITHOUT WARRANTY OF ANY KIND. WE ARE NOT
              LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES.
              OUR TOTAL LIABILITY SHALL NOT EXCEED THE AMOUNT YOU PAID US IN THE PAST 12 MONTHS.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">10. Termination and Data Export</h2>
            <p className="text-muted-foreground leading-relaxed">
              We may terminate or suspend your account at any time for violations of these
              terms. Upon termination, your right to use the Service ceases immediately.
              You may request a data export of your conversations within 30 days of account
              closure by emailing <strong>info@llmhive.ai</strong>.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">11. Changes to Terms</h2>
            <p className="text-muted-foreground leading-relaxed">
              We may update these Terms from time to time. We will notify you of material
              changes via email or in-app notification at least 15 days before they take effect.
              Continued use after the effective date constitutes acceptance of the new terms.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">12. Contact</h2>
            <p className="text-muted-foreground leading-relaxed">
              For questions about these Terms, contact us at:
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

