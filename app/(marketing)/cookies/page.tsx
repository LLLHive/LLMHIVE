"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { ArrowLeft } from "lucide-react"

export default function CookiePolicyPage() {
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
        <h1 className="text-4xl font-bold mb-2">Cookie Policy</h1>
        <p className="text-muted-foreground mb-8">Last updated: January 7, 2026</p>

        <div className="prose prose-invert max-w-none space-y-8">
          <section>
            <h2 className="text-2xl font-semibold mb-4">1. What Are Cookies</h2>
            <p className="text-muted-foreground leading-relaxed">
              Cookies are small text files that are stored on your device when you visit a website. 
              They help websites remember information about your visit, which can make it easier 
              to visit the site again and make the site more useful to you.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">2. How We Use Cookies</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              LLMHive uses cookies and similar technologies for several purposes:
            </p>
            
            <h3 className="text-lg font-medium mb-2">2.1 Essential Cookies</h3>
            <p className="text-muted-foreground leading-relaxed mb-4">
              These cookies are necessary for the website to function properly. They enable core 
              functionality such as authentication, security, and session management. You cannot 
              opt out of these cookies.
            </p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2 mb-4">
              <li><strong>Authentication cookies:</strong> Keep you signed in securely</li>
              <li><strong>Security cookies:</strong> Protect against CSRF and other attacks</li>
              <li><strong>Session cookies:</strong> Maintain your session state</li>
            </ul>

            <h3 className="text-lg font-medium mb-2">2.2 Preference Cookies</h3>
            <p className="text-muted-foreground leading-relaxed mb-4">
              These cookies remember your settings and preferences:
            </p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2 mb-4">
              <li><strong>Theme preference:</strong> Remember if you prefer dark or light mode</li>
              <li><strong>Language settings:</strong> Remember your language preference</li>
              <li><strong>UI preferences:</strong> Remember sidebar state, layout preferences</li>
            </ul>

            <h3 className="text-lg font-medium mb-2">2.3 Analytics Cookies</h3>
            <p className="text-muted-foreground leading-relaxed mb-4">
              We use Vercel Analytics to understand how visitors use our website. These cookies 
              help us improve our service:
            </p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li>Page views and navigation patterns</li>
              <li>Feature usage statistics</li>
              <li>Performance metrics</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">3. Third-Party Cookies</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              Some of our pages may contain content from third-party services that may set 
              their own cookies:
            </p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li><strong>Clerk:</strong> Authentication service</li>
              <li><strong>Stripe:</strong> Payment processing</li>
              <li><strong>Vercel:</strong> Hosting and analytics</li>
              <li><strong>Sentry:</strong> Error tracking (in production)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">4. Managing Cookies</h2>
            <p className="text-muted-foreground leading-relaxed mb-4">
              You can control and manage cookies in several ways:
            </p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2 mb-4">
              <li><strong>Browser settings:</strong> Most browsers allow you to refuse cookies 
              or delete existing cookies. Check your browser&apos;s help documentation for instructions.</li>
              <li><strong>Device settings:</strong> Your mobile device may have settings that 
              allow you to control advertising tracking.</li>
            </ul>
            <p className="text-muted-foreground leading-relaxed">
              Please note that disabling cookies may affect the functionality of LLMHive and 
              prevent you from using certain features.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">5. Cookie Retention</h2>
            <p className="text-muted-foreground leading-relaxed">
              Different cookies have different retention periods:
            </p>
            <ul className="list-disc pl-6 text-muted-foreground space-y-2">
              <li><strong>Session cookies:</strong> Deleted when you close your browser</li>
              <li><strong>Persistent cookies:</strong> Remain until their expiration date or 
              until you delete them (typically 30 days to 1 year)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">6. Updates to This Policy</h2>
            <p className="text-muted-foreground leading-relaxed">
              We may update this Cookie Policy from time to time. We will notify you of any 
              changes by posting the new policy on this page and updating the &quot;Last updated&quot; date.
            </p>
          </section>

          <section>
            <h2 className="text-2xl font-semibold mb-4">7. Contact Us</h2>
            <p className="text-muted-foreground leading-relaxed">
              If you have questions about our use of cookies, please contact us at:
              <br /><br />
              <strong>Email:</strong> privacy@llmhive.ai
            </p>
          </section>
        </div>
      </main>
    </div>
  )
}

