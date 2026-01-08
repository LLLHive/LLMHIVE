"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { 
  Users, 
  UserPlus, 
  Mail, 
  Link2, 
  Crown, 
  Shield, 
  UserIcon, 
  MoreHorizontal,
  MessageSquare,
  Send,
  Wifi,
  WifiOff,
  Loader2,
  Copy,
  Check,
} from "lucide-react"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { toast } from "@/lib/toast"
import { useCollaboration, CollaborationUser, CollaborationMessage } from "@/lib/hooks/use-collaboration"
import { cn } from "@/lib/utils"

export function CollaborationPanel() {
  const {
    sessionId,
    users,
    messages,
    isConnected,
    isConnecting,
    error,
    connect,
    disconnect,
    sendMessage,
    sendTypingStart,
    sendTypingStop,
    createSession,
  } = useCollaboration({
    onUserJoin: (user) => {
      toast.success(`${user.name} joined the session`)
    },
    onUserLeave: (userId) => {
      const user = users.find(u => u.id === userId)
      if (user) {
        toast.info(`${user.name} left the session`)
      }
    },
  })

  const [inviteEmail, setInviteEmail] = useState("")
  const [chatInput, setChatInput] = useState("")
  const [joinSessionId, setJoinSessionId] = useState("")
  const [copiedLink, setCopiedLink] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Auto-scroll to new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const handleCreateSession = async () => {
    const newSessionId = await createSession()
    if (newSessionId) {
      await connect(newSessionId)
      toast.success("Session created!")
    }
  }

  const handleJoinSession = async () => {
    if (!joinSessionId.trim()) {
      toast.error("Please enter a session ID")
      return
    }
    await connect(joinSessionId.trim())
  }

  const handleInvite = () => {
    if (!inviteEmail.trim()) return
    
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    if (!emailRegex.test(inviteEmail)) {
      toast.error("Please enter a valid email address")
      return
    }
    
    // Send invite email
    const subject = encodeURIComponent("Join my LLMHive collaboration session")
    const shareUrl = `${window.location.origin}/collaborate?session=${sessionId}`
    const body = encodeURIComponent(`I'd like to invite you to collaborate on LLMHive.\n\nJoin here: ${shareUrl}`)
    window.open(`mailto:${inviteEmail}?subject=${subject}&body=${body}`, "_blank")
    
    toast.success(`Invitation sent to ${inviteEmail}`)
    setInviteEmail("")
  }

  const handleCopyLink = async () => {
    if (!sessionId) return
    
    const shareLink = `${window.location.origin}/collaborate?session=${sessionId}`
    try {
      await navigator.clipboard.writeText(shareLink)
      setCopiedLink(true)
      toast.success("Share link copied!")
      setTimeout(() => setCopiedLink(false), 2000)
    } catch {
      toast.error("Failed to copy link")
    }
  }

  const handleSendChat = () => {
    if (!chatInput.trim()) return
    sendMessage(chatInput.trim())
    setChatInput("")
    sendTypingStop()
  }

  const handleChatInputChange = (value: string) => {
    setChatInput(value)
    
    // Typing indicator
    if (value.trim()) {
      sendTypingStart()
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current)
      }
      typingTimeoutRef.current = setTimeout(() => {
        sendTypingStop()
      }, 2000)
    } else {
      sendTypingStop()
    }
  }

  // Not connected - show join/create options
  if (!isConnected && !isConnecting) {
    return (
      <div className="h-full flex flex-col">
        <div className="p-6 border-b border-border">
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Users className="h-6 w-6" />
            Collaboration
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time collaboration with your team
          </p>
        </div>

        <div className="flex-1 flex flex-col items-center justify-center p-6 space-y-6">
          <div className="text-center space-y-2">
            <WifiOff className="h-12 w-12 mx-auto text-muted-foreground" />
            <h3 className="font-semibold">Not Connected</h3>
            <p className="text-sm text-muted-foreground">
              Create or join a session to collaborate in real-time
            </p>
          </div>

          <div className="w-full max-w-xs space-y-4">
            <Button onClick={handleCreateSession} className="w-full bronze-gradient">
              <Users className="h-4 w-4 mr-2" />
              Create New Session
            </Button>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <span className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-muted-foreground">or</span>
              </div>
            </div>

            <div className="space-y-2">
              <Input
                placeholder="Enter session ID"
                value={joinSessionId}
                onChange={(e) => setJoinSessionId(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleJoinSession()}
              />
              <Button 
                variant="outline" 
                className="w-full bg-transparent"
                onClick={handleJoinSession}
              >
                Join Session
              </Button>
            </div>
          </div>

          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
        </div>
      </div>
    )
  }

  // Connecting state
  if (isConnecting) {
    return (
      <div className="h-full flex flex-col items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-[var(--bronze)]" />
        <p className="mt-2 text-sm text-muted-foreground">Connecting...</p>
      </div>
    )
  }

  // Connected - show collaboration interface
  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Wifi className="h-4 w-4 text-green-500" />
          <span className="text-sm font-medium">Connected</span>
          <Badge variant="secondary" className="text-xs">
            {users.length} online
          </Badge>
        </div>
        <Button variant="ghost" size="sm" onClick={disconnect}>
          Leave
        </Button>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="team" className="flex-1 flex flex-col">
        <TabsList className="grid w-full grid-cols-2 mx-4 mt-2" style={{ width: "calc(100% - 2rem)" }}>
          <TabsTrigger value="team">Team</TabsTrigger>
          <TabsTrigger value="chat">Chat</TabsTrigger>
        </TabsList>

        {/* Team Tab */}
        <TabsContent value="team" className="flex-1 flex flex-col mt-0">
          <ScrollArea className="flex-1">
            <div className="p-4 space-y-4">
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
                  <Button onClick={handleInvite} size="icon">
                    <UserPlus className="h-4 w-4" />
                  </Button>
                </div>

                <div className="flex gap-2">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    className="flex-1 bg-transparent" 
                    onClick={handleCopyLink}
                  >
                    {copiedLink ? (
                      <Check className="h-3 w-3 mr-2 text-green-500" />
                    ) : (
                      <Link2 className="h-3 w-3 mr-2" />
                    )}
                    {copiedLink ? "Copied!" : "Copy Link"}
                  </Button>
                </div>
              </div>

              <div className="h-px bg-border" />

              {/* Users List */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold">Team ({users.length})</h3>
                <div className="space-y-2">
                  {users.map((user) => (
                    <CollaboratorItem key={user.id} user={user} />
                  ))}
                </div>
              </div>

              <div className="h-px bg-border" />

              {/* Session Info */}
              <div className="space-y-2">
                <h3 className="text-sm font-semibold">Session Info</h3>
                <div className="text-xs text-muted-foreground space-y-1">
                  <div className="flex items-center justify-between">
                    <span>Session ID:</span>
                    <code className="bg-muted px-1.5 py-0.5 rounded">{sessionId?.slice(0, 8)}...</code>
                  </div>
                </div>
              </div>
            </div>
          </ScrollArea>
        </TabsContent>

        {/* Chat Tab */}
        <TabsContent value="chat" className="flex-1 flex flex-col mt-0">
          <ScrollArea className="flex-1 px-4">
            <div className="space-y-3 py-4">
              {messages.length === 0 ? (
                <div className="text-center text-sm text-muted-foreground py-8">
                  <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No messages yet</p>
                  <p className="text-xs">Start the conversation!</p>
                </div>
              ) : (
                messages.map((msg) => (
                  <ChatMessage key={msg.id} message={msg} />
                ))
              )}
              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>

          {/* Typing indicator */}
          {users.some(u => u.status === "typing") && (
            <div className="px-4 py-1 text-xs text-muted-foreground">
              {users.filter(u => u.status === "typing").map(u => u.name).join(", ")} typing...
            </div>
          )}

          {/* Chat Input */}
          <div className="p-4 border-t border-border">
            <div className="flex gap-2">
              <Input
                placeholder="Type a message..."
                value={chatInput}
                onChange={(e) => handleChatInputChange(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSendChat()}
              />
              <Button onClick={handleSendChat} size="icon" disabled={!chatInput.trim()}>
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

function CollaboratorItem({ user }: { user: CollaborationUser }) {
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case "online":
        return "bg-green-500"
      case "typing":
        return "bg-yellow-500 animate-pulse"
      default:
        return "bg-gray-400"
    }
  }

  return (
    <div className="flex items-center justify-between p-2 rounded-lg border border-border hover:border-[var(--bronze)] transition-colors">
      <div className="flex items-center gap-2">
        <div className="relative">
          <Avatar className="h-8 w-8">
            <AvatarImage src={user.avatar || "/placeholder.svg"} />
            <AvatarFallback className="text-xs">{user.name[0]}</AvatarFallback>
          </Avatar>
          <div
            className={cn(
              "absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full border-2 border-background",
              getStatusColor(user.status)
            )}
          />
        </div>
        <div>
          <p className="text-sm font-medium leading-none">{user.name}</p>
          <p className="text-xs text-muted-foreground">{user.email}</p>
        </div>
      </div>

      <Badge variant="secondary" className={cn("text-xs", getRoleColor(user.role))}>
        {getRoleIcon(user.role)}
        <span className="ml-1 capitalize">{user.role}</span>
      </Badge>
    </div>
  )
}

function ChatMessage({ message }: { message: CollaborationMessage }) {
  const isSystem = message.type === "system"
  
  if (isSystem) {
    return (
      <div className="text-center text-xs text-muted-foreground py-1">
        {message.content}
      </div>
    )
  }

  return (
    <div className="flex gap-2">
      <Avatar className="h-6 w-6 flex-shrink-0 mt-0.5">
        <AvatarFallback className="text-xs">{message.userName[0]}</AvatarFallback>
      </Avatar>
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-medium">{message.userName}</span>
          <span className="text-xs text-muted-foreground">
            {message.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
        </div>
        <p className="text-sm text-foreground/80 break-words">{message.content}</p>
      </div>
    </div>
  )
}
