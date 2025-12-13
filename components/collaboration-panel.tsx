"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Users, UserPlus, Mail, Link2, Crown, Shield, UserIcon, MoreHorizontal } from "lucide-react"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { toast } from "@/lib/toast"

interface Collaborator {
  id: string
  name: string
  email: string
  avatar?: string
  role: "owner" | "editor" | "viewer"
  status: "online" | "offline"
}

export function CollaborationPanel() {
  const [collaborators, setCollaborators] = useState<Collaborator[]>([
    {
      id: "1",
      name: "You",
      email: "you@example.com",
      role: "owner",
      status: "online",
    },
  ])
  const [inviteEmail, setInviteEmail] = useState("")

  const handleInvite = () => {
    if (!inviteEmail.trim()) return
    
    // Validate email format
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(inviteEmail)) {
      toast.error("Please enter a valid email address")
      return
    }
    
    // Add new collaborator (pending invite)
    const newCollaborator: Collaborator = {
      id: `collab-${Date.now()}`,
      name: inviteEmail.split("@")[0],
      email: inviteEmail,
      role: "viewer",
      status: "offline",
    }
    setCollaborators((prev) => [...prev, newCollaborator])
    toast.success(`Invitation sent to ${inviteEmail}`)
    setInviteEmail("")
  }

  const handleEmailInvite = () => {
    const subject = encodeURIComponent("Join my LLMHive workspace")
    const body = encodeURIComponent("I'd like to invite you to collaborate on LLMHive. Click here to join: [link]")
    window.open(`mailto:?subject=${subject}&body=${body}`, "_blank")
    toast.info("Opening email client...")
  }

  const handleCopyLink = async () => {
    const shareLink = `${window.location.origin}/share/${Date.now()}`
    try {
      await navigator.clipboard.writeText(shareLink)
      toast.success("Share link copied to clipboard!")
    } catch {
      toast.error("Failed to copy link")
    }
  }

  return (
    <div className="h-full flex flex-col">
      <div className="p-6 border-b border-border">
        <h2 className="text-2xl font-bold flex items-center gap-2">
          <Users className="h-6 w-6" />
          Collaboration
        </h2>
        <p className="text-sm text-muted-foreground mt-1">Share and collaborate with your team</p>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-6 space-y-6">
          {/* Invite Section */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold">Invite Collaborators</h3>
            <div className="flex gap-2">
              <Input
                type="email"
                placeholder="email@example.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleInvite()}
              />
              <Button onClick={handleInvite} className="bronze-gradient">
                <UserPlus className="h-4 w-4 mr-2" />
                Invite
              </Button>
            </div>

            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="flex-1 bg-transparent" onClick={handleEmailInvite}>
                <Mail className="h-3 w-3 mr-2" />
                Email Invite
              </Button>
              <Button variant="outline" size="sm" className="flex-1 bg-transparent" onClick={handleCopyLink}>
                <Link2 className="h-3 w-3 mr-2" />
                Copy Link
              </Button>
            </div>
          </div>

          <div className="h-px bg-border" />

          {/* Collaborators List */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold">Team Members ({collaborators.length})</h3>
            <div className="space-y-2">
              {collaborators.map((collaborator) => (
                <CollaboratorItem
                  key={collaborator.id}
                  collaborator={collaborator}
                  onRemove={() => setCollaborators(collaborators.filter((c) => c.id !== collaborator.id))}
                  onRoleChange={(role) => {
                    setCollaborators(collaborators.map((c) => (c.id === collaborator.id ? { ...c, role } : c)))
                  }}
                />
              ))}
            </div>
          </div>

          <div className="h-px bg-border" />

          {/* Permissions */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold">Sharing Settings</h3>
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/50">
                <div>
                  <p className="font-medium">Anyone with the link</p>
                  <p className="text-xs text-muted-foreground">Can view and comment</p>
                </div>
                <Button variant="outline" size="sm">
                  Change
                </Button>
              </div>
            </div>
          </div>
        </div>
      </ScrollArea>
    </div>
  )
}

function CollaboratorItem({
  collaborator,
  onRemove,
  onRoleChange,
}: {
  collaborator: Collaborator
  onRemove: () => void
  onRoleChange: (role: Collaborator["role"]) => void
}) {
  const getRoleIcon = (role: string) => {
    switch (role) {
      case "owner":
        return <Crown className="h-3 w-3" />
      case "editor":
        return <Shield className="h-3 w-3" />
      default:
        return <UserIcon className="h-3 w-3" />
    }
  }

  const getRoleColor = (role: string) => {
    switch (role) {
      case "owner":
        return "bg-gradient-to-r from-[var(--bronze)] to-[var(--gold)]"
      case "editor":
        return "bg-blue-500/10 text-blue-500"
      default:
        return "bg-secondary"
    }
  }

  return (
    <div className="flex items-center justify-between p-3 rounded-lg border border-border hover:border-[var(--bronze)] transition-colors">
      <div className="flex items-center gap-3">
        <div className="relative">
          <Avatar className="h-10 w-10">
            <AvatarImage src={collaborator.avatar || "/placeholder.svg"} />
            <AvatarFallback>{collaborator.name[0]}</AvatarFallback>
          </Avatar>
          <div
            className={`absolute bottom-0 right-0 w-3 h-3 rounded-full border-2 border-background ${
              collaborator.status === "online" ? "bg-green-500" : "bg-gray-400"
            }`}
          />
        </div>
        <div>
          <p className="text-sm font-medium">{collaborator.name}</p>
          <p className="text-xs text-muted-foreground">{collaborator.email}</p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Badge variant="secondary" className={getRoleColor(collaborator.role)}>
          {getRoleIcon(collaborator.role)}
          <span className="ml-1 capitalize">{collaborator.role}</span>
        </Badge>

        {collaborator.role !== "owner" && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="h-7 w-7">
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onRoleChange("editor")}>
                <Shield className="h-4 w-4 mr-2" />
                Make Editor
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onRoleChange("viewer")}>
                <UserIcon className="h-4 w-4 mr-2" />
                Make Viewer
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onRemove} className="text-destructive">
                Remove
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>
    </div>
  )
}
