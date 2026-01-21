"use client"

import Link from "next/link"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { 
  ArrowLeft, 
  Mail, 
  MessageSquare, 
  Building2,
  Send,
  CheckCircle2
} from "lucide-react"

export default function ContactPage() {
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(false)

  const [ticketId, setTicketId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    
    const form = e.currentTarget
    const formData = new FormData(form)
    
    try {
      const response = await fetch("/api/support", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: formData.get("name"),
          email: formData.get("email"),
          subject: formData.get("subject"),
          message: formData.get("message"),
          type: "general",
        }),
      })
      
      const data = await response.json()
      
      if (response.ok && data.success) {
        setTicketId(data.ticketId)
        setSubmitted(true)
      } else {
        setError(data.error || "Failed to send message. Please try again.")
      }
    } catch (err) {
      setError("Network error. Please check your connection and try again.")
    } finally {
      setLoading(false)
    }
  }

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
        <h1 className="text-4xl font-bold mb-2">Contact Us</h1>
        <p className="text-muted-foreground mb-12">
          Have questions? We&apos;d love to hear from you. Send us a message and we&apos;ll respond as soon as possible.
        </p>

        <div className="grid md:grid-cols-3 gap-12">
          {/* Contact Info */}
          <div className="space-y-8">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-lg bg-[var(--bronze)]/10 flex items-center justify-center">
                  <Mail className="h-5 w-5 text-[var(--bronze)]" />
                </div>
                <h3 className="font-semibold">Email</h3>
              </div>
              <p className="text-sm text-muted-foreground">
                General inquiries<br />
                <a href="mailto:hello@llmhive.ai" className="text-[var(--bronze)] hover:underline">
                  hello@llmhive.ai
                </a>
              </p>
            </div>

            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-lg bg-[var(--bronze)]/10 flex items-center justify-center">
                  <MessageSquare className="h-5 w-5 text-[var(--bronze)]" />
                </div>
                <h3 className="font-semibold">Support</h3>
              </div>
              <p className="text-sm text-muted-foreground">
                Technical support<br />
                <a href="mailto:support@llmhive.ai" className="text-[var(--bronze)] hover:underline">
                  support@llmhive.ai
                </a>
              </p>
            </div>

            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-lg bg-[var(--bronze)]/10 flex items-center justify-center">
                  <Building2 className="h-5 w-5 text-[var(--bronze)]" />
                </div>
                <h3 className="font-semibold">Enterprise</h3>
              </div>
              <p className="text-sm text-muted-foreground">
                Sales & partnerships<br />
                <a href="mailto:enterprise@llmhive.ai" className="text-[var(--bronze)] hover:underline">
                  enterprise@llmhive.ai
                </a>
              </p>
            </div>
          </div>

          {/* Contact Form */}
          <div className="md:col-span-2">
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4 mb-4">
                <p className="text-red-500 text-sm">{error}</p>
              </div>
            )}
            {submitted ? (
              <div className="bg-card border border-border rounded-xl p-8 text-center">
                <div className="w-16 h-16 rounded-full bg-green-500/10 flex items-center justify-center mx-auto mb-4">
                  <CheckCircle2 className="h-8 w-8 text-green-500" />
                </div>
                <h2 className="text-2xl font-semibold mb-2">Message Sent!</h2>
                {ticketId && (
                  <p className="text-sm font-mono bg-muted px-3 py-1 rounded inline-block mb-4">
                    Ticket ID: {ticketId}
                  </p>
                )}
                <p className="text-muted-foreground mb-6">
                  Thank you for reaching out. We&apos;ll get back to you within 24 hours.
                  Save your ticket ID for reference.
                </p>
                <Button variant="outline" onClick={() => { setSubmitted(false); setTicketId(null); }}>
                  Send Another Message
                </Button>
              </div>
            ) : (
              <form onSubmit={handleSubmit} className="bg-card border border-border rounded-xl p-8 space-y-6">
                <div className="grid sm:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label htmlFor="name" className="text-sm font-medium">
                      Name
                    </label>
                    <Input 
                      id="name" 
                      name="name"
                      placeholder="Your name" 
                      required 
                      className="bg-background"
                    />
                  </div>
                  <div className="space-y-2">
                    <label htmlFor="email" className="text-sm font-medium">
                      Email
                    </label>
                    <Input 
                      id="email" 
                      name="email"
                      type="email" 
                      placeholder="you@example.com" 
                      required 
                      className="bg-background"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label htmlFor="subject" className="text-sm font-medium">
                    Subject
                  </label>
                  <Input 
                    id="subject" 
                    name="subject"
                    placeholder="How can we help?" 
                    required 
                    className="bg-background"
                  />
                </div>

                <div className="space-y-2">
                  <label htmlFor="message" className="text-sm font-medium">
                    Message
                  </label>
                  <Textarea 
                    id="message" 
                    name="message"
                    placeholder="Tell us more about your inquiry..." 
                    rows={6}
                    required 
                    className="bg-background resize-none"
                  />
                </div>

                <Button 
                  type="submit" 
                  className="w-full bg-[var(--bronze)] hover:bg-[var(--bronze)]/90 text-white"
                  disabled={loading}
                >
                  {loading ? (
                    <>Sending...</>
                  ) : (
                    <>
                      <Send className="h-4 w-4 mr-2" />
                      Send Message
                    </>
                  )}
                </Button>
              </form>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}

