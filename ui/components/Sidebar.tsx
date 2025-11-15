'use client'

import Image from "next/image"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import type { Conversation } from "@/lib/types"
import type { LucideIcon } from "lucide-react"
import {
  Plus,
  Pin,
  PinOff,
  Trash2,
  MessageSquare,
  Grid,
  Compass,
  Users,
  Settings,
  Share2,
} from "lucide-react"
const PRIMARY_NAV = [
  { label: "Chats", icon: MessageSquare, href: "/" },
  { label: "Projects", icon: Grid, href: "/projects" },
  { label: "Discover", icon: Compass, href: "/discover" },
]

const COLLAB_NAV = [
  { label: "Collaborate", icon: Users, href: "/collaborate" },
  { label: "Settings", icon: Settings, href: "/settings" },
  { label: "Share", icon: Share2, href: "/share" },
]


interface SidebarProps {
  conversations: Conversation[]
  currentConversationId: string | null
  onNewChat: () => void
  onSelectConversation: (id: string) => void
  onDeleteConversation: (id: string) => void
  onTogglePin: (id: string) => void
}

const formatTimestamp = (date: Date) => {
  try {
    return new Date(date).toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
    })
  } catch {
    return ""
  }
}

export function Sidebar({
  conversations,
  currentConversationId,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  onTogglePin,
}: SidebarProps) {
  const pinned = conversations.filter((conv) => conv.pinned)
  const others = conversations.filter((conv) => !conv.pinned)

  return (
    <aside className="w-[280px] border-r border-border bg-card/60 backdrop-blur-xl flex flex-col">
      <div className="px-4 py-3 border-b border-border flex items-center gap-3">
        <Image src="/logo-with-text.png" alt="LLMHive" width={120} height={32} className="h-8 w-auto" priority />
      </div>
      <div className="px-4 py-3 border-b border-border">
        <Button className="w-full justify-center gap-2 bronze-gradient text-background shadow-lg" onClick={onNewChat}>
          <Plus className="h-4 w-4" />
          New Chat
        </Button>
      </div>

      <ScrollArea className="flex-1 px-3 py-2 space-y-6">
        <SidebarNav title="Workspace" items={PRIMARY_NAV} />
        <SidebarNav title="Team" items={COLLAB_NAV} />
        {pinned.length > 0 && (
          <ConversationSection
            label="Pinned"
            conversations={pinned}
            currentConversationId={currentConversationId}
            onSelectConversation={onSelectConversation}
            onDeleteConversation={onDeleteConversation}
            onTogglePin={onTogglePin}
          />
        )}

        <ConversationSection
          label="Recent"
          conversations={others}
          currentConversationId={currentConversationId}
          onSelectConversation={onSelectConversation}
          onDeleteConversation={onDeleteConversation}
          onTogglePin={onTogglePin}
          emptyMessage="Start a conversation to see it here."
        />
      </ScrollArea>
    </aside>
  )
}

interface ConversationSectionProps extends Omit<SidebarProps, "conversations" | "onNewChat"> {
  conversations: Conversation[]
  label: string
  emptyMessage?: string
}

function ConversationSection({
  label,
  conversations,
  currentConversationId,
  onSelectConversation,
  onDeleteConversation,
  onTogglePin,
  emptyMessage,
}: ConversationSectionProps) {
  return (
    <div className="mb-4">
      <div className="text-xs uppercase tracking-wide text-foreground/70 mb-2 px-2">{label}</div>
      {conversations.length === 0 ? (
        emptyMessage ? <p className="text-xs text-muted-foreground px-2">{emptyMessage}</p> : null
      ) : (
        <div className="space-y-1">
          {conversations.map((conversation) => {
            const isActive = conversation.id === currentConversationId
            return (
              <button
                key={conversation.id}
                type="button"
                onClick={() => onSelectConversation(conversation.id)}
                className={cn(
                  "w-full rounded-lg border border-transparent bg-secondary/40 px-3 py-2 text-left transition hover:border-[var(--bronze)]/40",
                  isActive && "bg-secondary border-[var(--bronze)]/60",
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1">
                    <p className="text-sm font-medium truncate text-foreground">{conversation.title || "Untitled chat"}</p>
                    <p className="text-xs text-foreground/70">
                      {conversation.messages.length} message{conversation.messages.length === 1 ? "" : "s"} ·{" "}
                      {formatTimestamp(conversation.updatedAt)}
                    </p>
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7"
                      onClick={(e) => {
                        e.stopPropagation()
                        onTogglePin(conversation.id)
                      }}
                      title={conversation.pinned ? "Unpin conversation" : "Pin conversation"}
                    >
                      {conversation.pinned ? <PinOff className="h-3.5 w-3.5" /> : <Pin className="h-3.5 w-3.5" />}
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7"
                      onClick={(e) => {
                        e.stopPropagation()
                        onDeleteConversation(conversation.id)
                      }}
                      title="Delete conversation"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default Sidebar

type NavItem = {
  label: string
  icon: LucideIcon
  href: string
}

function SidebarNav({ title, items }: { title: string; items: NavItem[] }) {
  return (
    <div className="space-y-2 px-1">
      <p className="text-[11px] uppercase tracking-[0.2em] text-foreground/50">{title}</p>
      <div className="space-y-1">
        {items.map((item) => {
          const Icon = item.icon
          return (
            <Link
              key={item.label}
              href={item.href}
              className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-foreground/80 hover:text-foreground hover:bg-card/80 transition-colors"
            >
              <Icon className="h-4 w-4 text-foreground/70" />
              <span>{item.label}</span>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
