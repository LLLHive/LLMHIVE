"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  ArrowLeft,
  MessageSquare,
  Clock,
  Plus,
  ExternalLink,
  HelpCircle,
  CheckCircle2,
  Loader2
} from "lucide-react"

type TicketPriority = "low" | "medium" | "high" | "urgent"
type TicketStatus = "open" | "in_progress" | "waiting" | "resolved" | "closed"

interface SupportTicket {
  id: string
  email: string
  name: string
  type: string
  subject: string
  message: string
  priority: TicketPriority
  status: TicketStatus
  createdAt: string
  updatedAt: string
}

const statusColors: Record<TicketStatus, string> = {
  open: "bg-blue-500/10 text-blue-500",
  in_progress: "bg-purple-500/10 text-purple-500",
  waiting: "bg-yellow-500/10 text-yellow-500",
  resolved: "bg-green-500/10 text-green-500",
  closed: "bg-gray-500/10 text-gray-500",
}

const statusLabels: Record<TicketStatus, string> = {
  open: "Open",
  in_progress: "In Progress",
  waiting: "Awaiting Response",
  resolved: "Resolved",
  closed: "Closed",
}

const priorityColors: Record<TicketPriority, string> = {
  urgent: "text-red-500",
  high: "text-orange-500",
  medium: "text-yellow-500",
  low: "text-green-500",
}

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000)
  
  if (seconds < 60) return "just now"
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`
  return `${Math.floor(seconds / 86400)}d ago`
}

export default function UserTicketsPage() {
  const [tickets, setTickets] = useState<SupportTicket[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchTickets() {
      try {
        const response = await fetch("/api/support")
        if (response.ok) {
          const data = await response.json()
          setTickets(data.tickets || [])
        } else if (response.status === 401) {
          setError("Please sign in to view your tickets")
        }
      } catch (err) {
        setError("Failed to load tickets")
      } finally {
        setLoading(false)
      }
    }
    fetchTickets()
  }, [])

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/">
              <Button variant="ghost" size="sm" className="gap-2">
                <ArrowLeft className="h-4 w-4" />
                Back
              </Button>
            </Link>
            <h1 className="text-xl font-semibold">My Support Tickets</h1>
          </div>
          <Link href="/contact">
            <Button size="sm" className="bg-[var(--bronze)] hover:bg-[var(--bronze)]/90 gap-2">
              <Plus className="h-4 w-4" />
              New Ticket
            </Button>
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <div className="bg-card border border-border rounded-xl p-8 text-center">
            <MessageSquare className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground mb-4">{error}</p>
            <Link href="/sign-in">
              <Button variant="outline">Sign In</Button>
            </Link>
          </div>
        ) : tickets.length === 0 ? (
          <div className="bg-card border border-border rounded-xl p-12 text-center">
            <div className="w-20 h-20 rounded-full bg-[var(--bronze)]/10 flex items-center justify-center mx-auto mb-6">
              <CheckCircle2 className="h-10 w-10 text-[var(--bronze)]" />
            </div>
            <h2 className="text-xl font-semibold mb-2">No Support Tickets</h2>
            <p className="text-muted-foreground mb-6 max-w-md mx-auto">
              You haven&apos;t submitted any support requests yet. Need help? 
              Our team is here to assist you.
            </p>
            <div className="flex flex-wrap gap-3 justify-center">
              <Link href="/contact">
                <Button className="bg-[var(--bronze)] hover:bg-[var(--bronze)]/90 gap-2">
                  <MessageSquare className="h-4 w-4" />
                  Contact Support
                </Button>
              </Link>
              <Link href="/help">
                <Button variant="outline" className="gap-2">
                  <HelpCircle className="h-4 w-4" />
                  Help Center
                </Button>
              </Link>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground mb-6">
              {tickets.length} ticket{tickets.length !== 1 ? "s" : ""} found
            </p>

            {tickets.map(ticket => (
              <div
                key={ticket.id}
                className="bg-card border border-border rounded-xl p-6 hover:border-[var(--bronze)]/30 transition-colors"
              >
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs font-mono text-muted-foreground">{ticket.id}</span>
                      <Badge className={statusColors[ticket.status]}>
                        {statusLabels[ticket.status]}
                      </Badge>
                    </div>
                    <h3 className="font-semibold mb-1">{ticket.subject}</h3>
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {ticket.message}
                    </p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <div className="text-xs text-muted-foreground flex items-center gap-1 justify-end">
                      <Clock className="h-3 w-3" />
                      {formatTimeAgo(ticket.createdAt)}
                    </div>
                    <div className={`text-xs mt-1 ${priorityColors[ticket.priority]}`}>
                      {ticket.priority.charAt(0).toUpperCase() + ticket.priority.slice(1)} Priority
                    </div>
                  </div>
                </div>

                {ticket.status === "resolved" && (
                  <div className="bg-green-500/5 border border-green-500/10 rounded-lg p-3 text-sm">
                    <div className="flex items-center gap-2 text-green-500 font-medium">
                      <CheckCircle2 className="h-4 w-4" />
                      Issue Resolved
                    </div>
                    <p className="text-muted-foreground mt-1">
                      This ticket has been resolved. If you still need help, please create a new ticket.
                    </p>
                  </div>
                )}

                {ticket.status === "waiting" && (
                  <div className="bg-yellow-500/5 border border-yellow-500/10 rounded-lg p-3 text-sm">
                    <div className="flex items-center gap-2 text-yellow-500 font-medium">
                      <Clock className="h-4 w-4" />
                      Awaiting Your Response
                    </div>
                    <p className="text-muted-foreground mt-1">
                      We&apos;ve responded to your ticket. Please check your email and reply if needed.
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Help section */}
        <div className="mt-12 grid md:grid-cols-2 gap-6">
          <Link 
            href="/help" 
            className="group bg-card border border-border rounded-xl p-6 hover:border-[var(--bronze)]/50 transition-colors"
          >
            <HelpCircle className="h-8 w-8 text-[var(--bronze)] mb-4" />
            <h3 className="font-semibold mb-2 group-hover:text-[var(--bronze)] transition-colors">
              Help Center
            </h3>
            <p className="text-sm text-muted-foreground">
              Browse FAQs and guides to find quick answers.
            </p>
          </Link>

          <a 
            href="mailto:support@llmhive.ai" 
            className="group bg-card border border-border rounded-xl p-6 hover:border-[var(--bronze)]/50 transition-colors"
          >
            <ExternalLink className="h-8 w-8 text-[var(--bronze)] mb-4" />
            <h3 className="font-semibold mb-2 group-hover:text-[var(--bronze)] transition-colors">
              Email Support
            </h3>
            <p className="text-sm text-muted-foreground">
              Reach us directly at support@llmhive.ai
            </p>
          </a>
        </div>
      </main>
    </div>
  )
}
