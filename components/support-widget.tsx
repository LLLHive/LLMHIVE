"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  MessageCircle,
  X,
  Send,
  HelpCircle,
  ExternalLink,
  CheckCircle2,
  Loader2
} from "lucide-react"
import Link from "next/link"

interface SupportWidgetProps {
  userEmail?: string
  userName?: string
}

export function SupportWidget({ userEmail, userName }: SupportWidgetProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [view, setView] = useState<"menu" | "form" | "success">("menu")
  const [loading, setLoading] = useState(false)
  const [ticketId, setTicketId] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setLoading(true)

    const form = e.currentTarget
    const formData = new FormData(form)

    try {
      const response = await fetch("/api/support", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: formData.get("name") || userName || "Anonymous",
          email: formData.get("email") || userEmail || "",
          subject: formData.get("subject"),
          message: formData.get("message"),
          type: "general",
          metadata: {
            source: "widget",
            page: typeof window !== "undefined" ? window.location.pathname : "",
          }
        }),
      })

      const data = await response.json()
      
      if (response.ok && data.success) {
        setTicketId(data.ticketId)
        setView("success")
        form.reset()
      }
    } catch (error) {
      console.error("Failed to submit support request:", error)
    } finally {
      setLoading(false)
    }
  }

  const resetWidget = () => {
    setView("menu")
    setTicketId(null)
  }

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 bg-[var(--bronze)] hover:bg-[var(--bronze)]/90 text-white rounded-full p-4 shadow-lg hover:shadow-xl transition-all hover:scale-105"
        aria-label="Open support"
      >
        <MessageCircle className="h-6 w-6" />
      </button>
    )
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-[360px] max-h-[500px] bg-card border border-border rounded-2xl shadow-2xl overflow-hidden animate-in slide-in-from-bottom-4 duration-300 flex flex-col">
      {/* Header */}
      <div className="bg-[var(--bronze)] text-white px-4 py-3 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-2">
          <MessageCircle className="h-5 w-5" />
          <span className="font-medium">Support</span>
        </div>
        <button
          onClick={() => { setIsOpen(false); resetWidget(); }}
          className="hover:bg-white/10 rounded-lg p-1 transition-colors"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      {/* Content */}
      <div className="p-4 overflow-y-auto flex-1">
        {view === "menu" && (
          <div className="space-y-3">
            <p className="text-sm text-muted-foreground mb-4">
              How can we help you today?
            </p>

            <button
              onClick={() => setView("form")}
              className="w-full flex items-center gap-3 p-3 rounded-lg border border-border hover:border-[var(--bronze)]/50 hover:bg-muted/50 transition-all text-left"
            >
              <div className="w-10 h-10 rounded-full bg-[var(--bronze)]/10 flex items-center justify-center">
                <Send className="h-5 w-5 text-[var(--bronze)]" />
              </div>
              <div>
                <div className="font-medium">Send a Message</div>
                <div className="text-xs text-muted-foreground">Get help from our team</div>
              </div>
            </button>

            <Link
              href="/help"
              className="w-full flex items-center gap-3 p-3 rounded-lg border border-border hover:border-[var(--bronze)]/50 hover:bg-muted/50 transition-all"
              onClick={() => setIsOpen(false)}
            >
              <div className="w-10 h-10 rounded-full bg-[var(--bronze)]/10 flex items-center justify-center">
                <HelpCircle className="h-5 w-5 text-[var(--bronze)]" />
              </div>
              <div>
                <div className="font-medium">Help Center</div>
                <div className="text-xs text-muted-foreground">Browse FAQs & guides</div>
              </div>
            </Link>

            <a
              href="mailto:info@llmhive.ai"
              className="w-full flex items-center gap-3 p-3 rounded-lg border border-border hover:border-[var(--bronze)]/50 hover:bg-muted/50 transition-all"
            >
              <div className="w-10 h-10 rounded-full bg-[var(--bronze)]/10 flex items-center justify-center">
                <ExternalLink className="h-5 w-5 text-[var(--bronze)]" />
              </div>
              <div>
                <div className="font-medium">Email Us</div>
                <div className="text-xs text-muted-foreground">info@llmhive.ai</div>
              </div>
            </a>
          </div>
        )}

        {view === "form" && (
          <form onSubmit={handleSubmit} className="space-y-3">
            <button
              type="button"
              onClick={() => setView("menu")}
              className="text-sm text-[var(--bronze)] hover:underline mb-2"
            >
              ← Back
            </button>

            {!userEmail && (
              <>
                <Input
                  name="name"
                  placeholder="Your name"
                  required
                  className="bg-background"
                />
                <Input
                  name="email"
                  type="email"
                  placeholder="your@email.com"
                  required
                  className="bg-background"
                />
              </>
            )}

            <Input
              name="subject"
              placeholder="Subject"
              required
              className="bg-background"
            />

            <Textarea
              name="message"
              placeholder="How can we help?"
              rows={4}
              required
              className="bg-background resize-none"
            />

            <Button
              type="submit"
              disabled={loading}
              className="w-full bg-[var(--bronze)] hover:bg-[var(--bronze)]/90"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4 mr-2" />
                  Send Message
                </>
              )}
            </Button>
          </form>
        )}

        {view === "success" && (
          <div className="text-center py-2">
            <div className="w-16 h-16 rounded-full bg-green-500/10 flex items-center justify-center mx-auto mb-3">
              <CheckCircle2 className="h-8 w-8 text-green-500" />
            </div>
            <h3 className="font-semibold mb-2">Message Sent!</h3>
            {ticketId && (
              <p className="text-xs font-mono bg-muted px-2 py-1 rounded inline-block mb-2">
                {ticketId}
              </p>
            )}
            <p className="text-sm text-muted-foreground mb-4">
              We&apos;ll respond within 24 hours.
            </p>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={resetWidget}
              className="bg-card hover:bg-accent hover:text-accent-foreground border-2 transition-all shadow hover:shadow-md"
            >
              Close
            </Button>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-2 border-t border-border bg-muted/30 flex-shrink-0">
        <p className="text-xs text-center text-muted-foreground">
          Powered by LLMHive Support
        </p>
      </div>
    </div>
  )
}
