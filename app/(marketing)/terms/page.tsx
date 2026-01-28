"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { ArrowLeft } from "lucide-react"

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-background">
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
        <p className="text-muted-foreground mb-8">Last updated: January 7, 2026</p>

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
              We offer a FREE tier and three paid subscription tiers designed to meet different needs:
            </p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2 mb-4">
              <li><strong>Free ($0/mo):</strong> 50 queries/month with our patented FREE orchestration that beats most paid models</li>
              <li><strong>Lite ($14.99/mo):</strong> 100 ELITE queries (#1 in ALL categories), then FREE tier after quota</li>
              <li><strong>Pro ($29.99/mo):</strong> 500 ELITE queries (#1 in ALL categories), then FREE tier after quota</li>
              <li><strong>Enterprise ($35/seat/mo, min 5 seats):</strong> 400 ELITE/seat, SSO &amp; compliance</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Payment terms:
            </p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>Paid subscriptions are billed in advance on a monthly or annual basis</li>
              <li>Annual subscriptions receive approximately 17% discount</li>
              <li>You may cancel your subscription at any time</li>
              <li>Refunds are provided at our discretion</li>
              <li>Prices may change with 30 days notice</li>
              <li>ELITE query quotas reset monthly; unused queries do not roll over</li>
              <li>Enterprise seats can be adjusted with billing prorated accordingly</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">6. Intellectual Property</h2>
            <p className="text-muted-foreground leading-relaxed">
              You retain ownership of content you create using the Service. You grant us a 
              limited license to process your content to provide the Service. The Service 
              itself, including its design, features, and code, is owned by LLMHive.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">7. AI Output Disclaimer</h2>
            <p className="text-muted-foreground leading-relaxed">
              AI-generated content may contain errors, biases, or inaccuracies. You are 
              responsible for reviewing and verifying any AI output before use. The Service 
              should not be used as a substitute for professional advice (legal, medical, 
              financial, etc.).
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">8. Limitation of Liability</h2>
            <p className="text-muted-foreground leading-relaxed">
              THE SERVICE IS PROVIDED &quot;AS IS&quot; WITHOUT WARRANTY OF ANY KIND. WE ARE NOT 
              LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES. 
              OUR TOTAL LIABILITY SHALL NOT EXCEED THE AMOUNT YOU PAID US IN THE PAST 12 MONTHS.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">9. Termination</h2>
            <p className="text-muted-foreground leading-relaxed">
              We may terminate or suspend your account at any time for violations of these 
              terms. Upon termination, your right to use the Service ceases immediately. 
              You may export your data before account closure.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">10. Changes to Terms</h2>
            <p className="text-muted-foreground leading-relaxed">
              We may update these Terms from time to time. We will notify you of material 
              changes via email or in-app notification. Continued use after changes constitutes 
              acceptance of the new terms.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">11. Contact</h2>
            <p className="text-muted-foreground leading-relaxed">
              For questions about these Terms, contact us at:
              <br /><br />
              <strong>Email:</strong> info@llmhive.ai
              <br />
              <strong>Address:</strong> [Your Business Address]
            </p>
          </section>
        </div>
      </main>
    </div>
  )
}

