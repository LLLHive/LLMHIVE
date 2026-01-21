"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  ArrowLeft,
  Search,
  MessageSquare,
  Clock,
  User,
  AlertCircle,
  CheckCircle2,
  ArrowUpRight,
  Filter,
  RefreshCw,
  Mail,
  MoreVertical,
  Eye,
  Reply,
  Archive,
  Trash2
} from "lucide-react"

// Ticket types matching the API
type TicketType = "general" | "technical" | "billing" | "enterprise" | "bug" | "feature"
type TicketPriority = "low" | "medium" | "high" | "urgent"
type TicketStatus = "open" | "in_progress" | "waiting" | "resolved" | "closed"

interface SupportTicket {
  id: string
  userId?: string
  email: string
  name: string
  type: TicketType
  subject: string
  message: string
  priority: TicketPriority
  status: TicketStatus
  createdAt: string
  updatedAt: string
}

// Mock data for demo
const mockTickets: SupportTicket[] = [
  {
    id: "TKT-M2X1A-B4C7",
    email: "john@example.com",
    name: "John Smith",
    type: "billing",
    subject: "Question about Enterprise pricing",
    message: "Hi, I'm interested in the Enterprise plan for our team of 20 people. Can you provide a custom quote?",
    priority: "high",
    status: "open",
    createdAt: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // 30 mins ago
    updatedAt: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
  },
  {
    id: "TKT-N3Y2B-C5D8",
    userId: "user_abc123",
    email: "sarah@startup.io",
    name: "Sarah Johnson",
    type: "technical",
    subject: "API rate limiting issue",
    message: "We're hitting rate limits even though we haven't exceeded our quota. Our user ID is user_abc123. Can you check?",
    priority: "urgent",
    status: "in_progress",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(), // 2 hours ago
    updatedAt: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
  },
  {
    id: "TKT-O4Z3C-D6E9",
    email: "mike@corp.com",
    name: "Mike Chen",
    type: "bug",
    subject: "Chat history not loading",
    message: "When I try to view my chat history, the page shows a loading spinner indefinitely. I've tried refreshing and clearing cache.",
    priority: "medium",
    status: "waiting",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(), // 5 hours ago
    updatedAt: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
  },
  {
    id: "TKT-P5A4D-E7F0",
    email: "emma@agency.co",
    name: "Emma Wilson",
    type: "feature",
    subject: "Request: Export conversations as PDF",
    message: "Would love the ability to export conversations as PDFs for documentation purposes. Is this on the roadmap?",
    priority: "low",
    status: "open",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(), // 1 day ago
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
  },
  {
    id: "TKT-Q6B5E-F8G1",
    userId: "user_xyz789",
    email: "alex@enterprise.net",
    name: "Alex Rivera",
    type: "enterprise",
    subject: "SSO Integration Questions",
    message: "We're evaluating LLMHive for our organization. We need SAML SSO with Okta. Can you provide documentation on the setup process?",
    priority: "high",
    status: "resolved",
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(), // 2 days ago
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(),
  },
]

const priorityColors: Record<TicketPriority, string> = {
  urgent: "bg-red-500/10 text-red-500 border-red-500/20",
  high: "bg-orange-500/10 text-orange-500 border-orange-500/20",
  medium: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
  low: "bg-green-500/10 text-green-500 border-green-500/20",
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
  waiting: "Waiting",
  resolved: "Resolved",
  closed: "Closed",
}

const typeIcons: Record<TicketType, React.ReactNode> = {
  general: <MessageSquare className="h-4 w-4" />,
  technical: <AlertCircle className="h-4 w-4" />,
  billing: <MessageSquare className="h-4 w-4" />,
  enterprise: <ArrowUpRight className="h-4 w-4" />,
  bug: <AlertCircle className="h-4 w-4" />,
  feature: <CheckCircle2 className="h-4 w-4" />,
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

export default function AdminSupportPage() {
  const [tickets, setTickets] = useState<SupportTicket[]>(mockTickets)
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState<TicketStatus | "all">("all")
  const [priorityFilter, setPriorityFilter] = useState<TicketPriority | "all">("all")
  const [selectedTicket, setSelectedTicket] = useState<SupportTicket | null>(null)
  const [loading, setLoading] = useState(false)

  // Stats
  const stats = {
    open: tickets.filter(t => t.status === "open").length,
    inProgress: tickets.filter(t => t.status === "in_progress").length,
    urgent: tickets.filter(t => t.priority === "urgent" && t.status !== "resolved" && t.status !== "closed").length,
    avgResponseTime: "2.4h",
  }

  // Filtered tickets
  const filteredTickets = tickets.filter(ticket => {
    const matchesSearch = 
      searchQuery === "" ||
      ticket.subject.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ticket.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ticket.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ticket.id.toLowerCase().includes(searchQuery.toLowerCase())
    
    const matchesStatus = statusFilter === "all" || ticket.status === statusFilter
    const matchesPriority = priorityFilter === "all" || ticket.priority === priorityFilter
    
    return matchesSearch && matchesStatus && matchesPriority
  })

  const updateTicketStatus = (ticketId: string, newStatus: TicketStatus) => {
    setTickets(prev => prev.map(t => 
      t.id === ticketId 
        ? { ...t, status: newStatus, updatedAt: new Date().toISOString() }
        : t
    ))
    if (selectedTicket?.id === ticketId) {
      setSelectedTicket(prev => prev ? { ...prev, status: newStatus } : null)
    }
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/admin/dashboard">
              <Button variant="ghost" size="sm" className="gap-2">
                <ArrowLeft className="h-4 w-4" />
                Dashboard
              </Button>
            </Link>
            <h1 className="text-xl font-semibold">Support Tickets</h1>
          </div>
          <Button variant="outline" size="sm" className="gap-2" onClick={() => setLoading(true)}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-card border border-border rounded-xl p-4">
            <div className="text-sm text-muted-foreground mb-1">Open Tickets</div>
            <div className="text-2xl font-bold text-blue-500">{stats.open}</div>
          </div>
          <div className="bg-card border border-border rounded-xl p-4">
            <div className="text-sm text-muted-foreground mb-1">In Progress</div>
            <div className="text-2xl font-bold text-purple-500">{stats.inProgress}</div>
          </div>
          <div className="bg-card border border-border rounded-xl p-4">
            <div className="text-sm text-muted-foreground mb-1">Urgent</div>
            <div className="text-2xl font-bold text-red-500">{stats.urgent}</div>
          </div>
          <div className="bg-card border border-border rounded-xl p-4">
            <div className="text-sm text-muted-foreground mb-1">Avg Response</div>
            <div className="text-2xl font-bold text-green-500">{stats.avgResponseTime}</div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-4 mb-6">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search tickets..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as TicketStatus | "all")}
            className="px-3 py-2 rounded-lg border border-border bg-card text-sm"
          >
            <option value="all">All Status</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="waiting">Waiting</option>
            <option value="resolved">Resolved</option>
            <option value="closed">Closed</option>
          </select>
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value as TicketPriority | "all")}
            className="px-3 py-2 rounded-lg border border-border bg-card text-sm"
          >
            <option value="all">All Priority</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>

        {/* Ticket List and Detail View */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Ticket List */}
          <div className="lg:col-span-2 space-y-3">
            {filteredTickets.length === 0 ? (
              <div className="bg-card border border-border rounded-xl p-8 text-center">
                <MessageSquare className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">No tickets found</p>
              </div>
            ) : (
              filteredTickets.map(ticket => (
                <div
                  key={ticket.id}
                  onClick={() => setSelectedTicket(ticket)}
                  className={`bg-card border rounded-xl p-4 cursor-pointer transition-all hover:border-[var(--bronze)]/50 ${
                    selectedTicket?.id === ticket.id 
                      ? "border-[var(--bronze)] ring-1 ring-[var(--bronze)]/20" 
                      : "border-border"
                  }`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-mono text-muted-foreground">{ticket.id}</span>
                        <Badge variant="outline" className={priorityColors[ticket.priority]}>
                          {ticket.priority}
                        </Badge>
                        <Badge className={statusColors[ticket.status]}>
                          {statusLabels[ticket.status]}
                        </Badge>
                      </div>
                      <h3 className="font-medium truncate">{ticket.subject}</h3>
                      <p className="text-sm text-muted-foreground truncate mt-1">
                        {ticket.message}
                      </p>
                    </div>
                    <div className="text-right flex-shrink-0">
                      <div className="text-xs text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatTimeAgo(ticket.createdAt)}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-3 mt-3 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <User className="h-3 w-3" />
                      {ticket.name}
                    </span>
                    <span className="flex items-center gap-1">
                      <Mail className="h-3 w-3" />
                      {ticket.email}
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Ticket Detail */}
          <div className="lg:col-span-1">
            {selectedTicket ? (
              <div className="bg-card border border-border rounded-xl p-6 sticky top-24">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-mono text-muted-foreground">{selectedTicket.id}</span>
                  <Button variant="ghost" size="sm">
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </div>

                <h2 className="text-lg font-semibold mb-4">{selectedTicket.subject}</h2>

                <div className="space-y-4 mb-6">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className={priorityColors[selectedTicket.priority]}>
                      {selectedTicket.priority}
                    </Badge>
                    <Badge className={statusColors[selectedTicket.status]}>
                      {statusLabels[selectedTicket.status]}
                    </Badge>
                    <Badge variant="outline" className="capitalize">
                      {selectedTicket.type}
                    </Badge>
                  </div>

                  <div className="text-sm space-y-2">
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4 text-muted-foreground" />
                      <span>{selectedTicket.name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Mail className="h-4 w-4 text-muted-foreground" />
                      <a href={`mailto:${selectedTicket.email}`} className="text-[var(--bronze)] hover:underline">
                        {selectedTicket.email}
                      </a>
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      <span>Created {formatTimeAgo(selectedTicket.createdAt)}</span>
                    </div>
                  </div>
                </div>

                <div className="border-t border-border pt-4 mb-6">
                  <h3 className="text-sm font-medium mb-2">Message</h3>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                    {selectedTicket.message}
                  </p>
                </div>

                <div className="space-y-2">
                  <h3 className="text-sm font-medium mb-2">Actions</h3>
                  <div className="grid grid-cols-2 gap-2">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="gap-1"
                      onClick={() => updateTicketStatus(selectedTicket.id, "in_progress")}
                    >
                      <Eye className="h-3 w-3" />
                      Take
                    </Button>
                    <a href={`mailto:${selectedTicket.email}?subject=Re: ${selectedTicket.subject}`}>
                      <Button variant="outline" size="sm" className="gap-1 w-full">
                        <Reply className="h-3 w-3" />
                        Reply
                      </Button>
                    </a>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="gap-1"
                      onClick={() => updateTicketStatus(selectedTicket.id, "resolved")}
                    >
                      <CheckCircle2 className="h-3 w-3" />
                      Resolve
                    </Button>
                    <Button 
                      variant="outline" 
                      size="sm" 
                      className="gap-1"
                      onClick={() => updateTicketStatus(selectedTicket.id, "closed")}
                    >
                      <Archive className="h-3 w-3" />
                      Close
                    </Button>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-card border border-border rounded-xl p-8 text-center">
                <MessageSquare className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
                <p className="text-muted-foreground">Select a ticket to view details</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
