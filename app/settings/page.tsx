"use client"
import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import { useTheme } from "next-themes"
import Image from "next/image"
import { LogoText } from "@/components/branding"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { User, Key, Link2, Bell, Shield, Palette, Check, Github, Trash2, Save, CreditCard, ExternalLink, Loader2 } from "lucide-react"
import { Sidebar } from "@/components/sidebar"
import { UserAccountMenu } from "@/components/user-account-menu"
import { ROUTES } from "@/lib/routes"
import { useAuth } from "@/lib/auth-context"
import { toast } from "@/lib/toast"

// LocalStorage keys for settings persistence
const STORAGE_KEYS = {
  APPEARANCE: "llmhive-appearance-settings",
  NOTIFICATIONS: "llmhive-notification-settings",
  PRIVACY: "llmhive-privacy-settings",
  API_KEYS: "llmhive-api-keys",
  CONNECTIONS: "llmhive-connections",
}

// Card data with new icon badge colors
const settingsCards = [
  {
    id: "account",
    title: "Account",
    description: "Manage your profile and account details",
    icon: User,
    badgeClass: "icon-badge-blue",
  },
  {
    id: "billing",
    title: "Billing",
    description: "Subscription and payment settings",
    icon: CreditCard,
    badgeClass: "icon-badge-green",
  },
  {
    id: "api-keys",
    title: "API Keys",
    description: "Configure external service API keys",
    icon: Key,
    badgeClass: "icon-badge-amber",
  },
  {
    id: "connections",
    title: "Connections",
    description: "GitHub, Google, Slack integrations",
    icon: Link2,
    badgeClass: "icon-badge-teal",
  },
  {
    id: "notifications",
    title: "Notifications",
    description: "Email, push, and update preferences",
    icon: Bell,
    badgeClass: "icon-badge-yellow",
  },
  {
    id: "privacy",
    title: "Privacy",
    description: "Data sharing and usage controls",
    icon: Shield,
    badgeClass: "icon-badge-pink",
  },
  {
    id: "appearance",
    title: "Appearance",
    description: "Theme, display, and accessibility",
    icon: Palette,
    badgeClass: "icon-badge-orange",
  },
]

// API Keys data
const apiKeys = [
  { id: "openai", label: "OpenAI", placeholder: "sk-...", connected: true },
  { id: "anthropic", label: "Anthropic", placeholder: "sk-ant-...", connected: false },
  { id: "google", label: "Google AI", placeholder: "AIza...", connected: false },
  { id: "cohere", label: "Cohere", placeholder: "...", connected: false },
]

// Connections data
const connections = [
  { id: "github", label: "GitHub", description: "Connect your repositories", icon: Github, connected: true },
  { id: "google", label: "Google", description: "Sign in with Google", connected: false },
  { id: "slack", label: "Slack", description: "Get notifications in Slack", connected: false },
]

// Notification options
const notificationOptions = [
  { id: "email", label: "Email Notifications", description: "Receive updates via email" },
  { id: "push", label: "Push Notifications", description: "Browser push notifications" },
  { id: "updates", label: "Product Updates", description: "News about new features" },
  { id: "marketing", label: "Marketing Emails", description: "Tips and promotional content" },
]

// Privacy options
const privacyOptions = [
  { id: "shareUsage", label: "Share Usage Data", description: "Help improve LLMHive with anonymous usage data" },
  { id: "shareChats", label: "Share Chats for Training", description: "Allow chats to be used for model improvement" },
  { id: "publicProfile", label: "Public Profile", description: "Make your profile visible to others" },
]

// Appearance options
const appearanceOptions = [
  { id: "compactMode", label: "Compact Mode", description: "Reduce spacing for more content" },
  { id: "animations", label: "Animations", description: "Enable UI animations and transitions" },
  { id: "soundEffects", label: "Sound Effects", description: "Play sounds for notifications" },
]

type DrawerId = "account" | "billing" | "api-keys" | "connections" | "notifications" | "privacy" | "appearance" | null

export default function SettingsPage() {
  const router = useRouter()
  const auth = useAuth()
  const { theme, setTheme, resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  const [activeDrawer, setActiveDrawer] = useState<DrawerId>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  // State for various settings - initialized from localStorage
  const [connectedKeys, setConnectedKeys] = useState<string[]>([])
  const [connectedServices, setConnectedServices] = useState<string[]>([])
  const [enabledNotifications, setEnabledNotifications] = useState<string[]>([])
  const [privacySettings, setPrivacySettings] = useState<string[]>([])
  const [appearanceSettings, setAppearanceSettings] = useState<string[]>([])
  
  // Load settings from localStorage on mount
  useEffect(() => {
    setMounted(true)
    
    try {
      const savedAppearance = localStorage.getItem(STORAGE_KEYS.APPEARANCE)
      const savedNotifications = localStorage.getItem(STORAGE_KEYS.NOTIFICATIONS)
      const savedPrivacy = localStorage.getItem(STORAGE_KEYS.PRIVACY)
      const savedApiKeys = localStorage.getItem(STORAGE_KEYS.API_KEYS)
      const savedConnections = localStorage.getItem(STORAGE_KEYS.CONNECTIONS)
      
      const parsedAppearance = savedAppearance ? JSON.parse(savedAppearance) : ["animations"]
      setAppearanceSettings(parsedAppearance)
      setEnabledNotifications(savedNotifications ? JSON.parse(savedNotifications) : ["email", "updates"])
      setPrivacySettings(savedPrivacy ? JSON.parse(savedPrivacy) : ["shareUsage"])
      setConnectedKeys(savedApiKeys ? JSON.parse(savedApiKeys) : ["openai"])
      setConnectedServices(savedConnections ? JSON.parse(savedConnections) : ["github"])
      
      document.documentElement.classList.toggle('compact-mode', parsedAppearance.includes('compactMode'))
      document.documentElement.classList.toggle('no-animations', !parsedAppearance.includes('animations'))
    } catch (e) {
      console.error("Failed to load settings:", e)
      setAppearanceSettings(["animations"])
      setEnabledNotifications(["email", "updates"])
      setPrivacySettings(["shareUsage"])
      setConnectedKeys(["openai"])
      setConnectedServices(["github"])
    }
  }, [])

  const toggleKey = useCallback((id: string) => {
    setConnectedKeys((prev) => {
      const next = prev.includes(id) ? prev.filter((k) => k !== id) : [...prev, id]
      localStorage.setItem(STORAGE_KEYS.API_KEYS, JSON.stringify(next))
      toast.success(`API key ${prev.includes(id) ? 'removed' : 'added'}`)
      return next
    })
  }, [])

  const toggleService = useCallback((id: string) => {
    setConnectedServices((prev) => {
      const next = prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]
      localStorage.setItem(STORAGE_KEYS.CONNECTIONS, JSON.stringify(next))
      toast.success(`Service ${prev.includes(id) ? 'disconnected' : 'connected'}`)
      return next
    })
  }, [])

  const toggleNotification = useCallback((id: string) => {
    setEnabledNotifications((prev) => {
      const next = prev.includes(id) ? prev.filter((n) => n !== id) : [...prev, id]
      localStorage.setItem(STORAGE_KEYS.NOTIFICATIONS, JSON.stringify(next))
      toast.success(`Notification setting updated`)
      return next
    })
  }, [])

  const togglePrivacy = useCallback((id: string) => {
    setPrivacySettings((prev) => {
      const next = prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
      localStorage.setItem(STORAGE_KEYS.PRIVACY, JSON.stringify(next))
      toast.success(`Privacy setting updated`)
      return next
    })
  }, [])

  const toggleAppearance = useCallback((id: string) => {
    setAppearanceSettings((prev) => {
      const next = prev.includes(id) ? prev.filter((a) => a !== id) : [...prev, id]
      localStorage.setItem(STORAGE_KEYS.APPEARANCE, JSON.stringify(next))
      
      if (id === 'compactMode') {
        document.documentElement.classList.toggle('compact-mode', !prev.includes(id))
      }
      if (id === 'animations') {
        document.documentElement.classList.toggle('no-animations', prev.includes(id))
      }
      
      toast.success(`${id === 'compactMode' ? 'Compact mode' : id === 'animations' ? 'Animations' : 'Sound effects'} ${prev.includes(id) ? 'disabled' : 'enabled'}`)
      return next
    })
  }, [])

  const getCount = (id: string) => {
    switch (id) {
      case "api-keys": return connectedKeys.length
      case "connections": return connectedServices.length
      case "notifications": return enabledNotifications.length
      case "privacy": return privacySettings.length
      case "appearance": return appearanceSettings.length
      default: return 0
    }
  }

  return (
    <div className="flex h-screen overflow-hidden relative">
      {/* Sign In Button - Top Right (fixed position) */}
      <div className="hidden md:block fixed top-3 right-3 z-50">
        <UserAccountMenu />
      </div>

      {/* Glassmorphism Sidebar */}
      <div className="llmhive-glass-sidebar h-full">
        <Sidebar
          conversations={[]}
          currentConversationId={null}
          onNewChat={() => router.push(ROUTES.HOME)}
          onSelectConversation={() => router.push(ROUTES.HOME)}
          onDeleteConversation={() => {}}
          onTogglePin={() => {}}
          onRenameConversation={() => {}}
          onMoveToProject={() => {}}
          projects={[]}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
          onGoHome={() => router.push(ROUTES.HOME)}
        />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {/* Settings Content */}
        <div className="flex-1 h-full overflow-auto">
          <div className="min-h-full flex flex-col items-center justify-start px-4 pt-4 pb-20">
            
            {/* Logo & Title */}
            <div className="text-center mb-6 llmhive-fade-in">
              <div className="relative w-52 h-52 md:w-[340px] md:h-[340px] lg:w-[378px] lg:h-[378px] mx-auto -mb-14 md:-mb-24 llmhive-float">
                <Image src="/logo.png" alt="LLMHive" fill className="object-contain drop-shadow-2xl" priority />
              </div>
              <LogoText height={64} className="md:hidden mb-2 mx-auto" />
              <LogoText height={92} className="hidden md:block lg:hidden mb-2 mx-auto" />
              <LogoText height={110} className="hidden lg:block mb-2 mx-auto" />
              <h2 className="text-xl md:text-2xl lg:text-3xl llmhive-subtitle mb-2">
                Settings
              </h2>
              <p className="llmhive-subtitle-3d text-sm md:text-base mx-auto whitespace-nowrap">
                Configure your account, integrations, and preferences
              </p>
            </div>

            {/* Settings Grid */}
            <div className="w-full max-w-4xl llmhive-fade-in" style={{ animationDelay: '0.1s' }}>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 md:gap-4">
                {settingsCards.map((card, index) => {
                  const Icon = card.icon
                  const count = getCount(card.id)
                  return (
                    <button
                      key={card.id}
                      onClick={() => setActiveDrawer(card.id as DrawerId)}
                      className="settings-card group llmhive-fade-in"
                      style={{ animationDelay: `${0.1 + index * 0.05}s` }}
                    >
                      {count > 0 && (
                        <Badge className="absolute top-2 right-2 bronze-gradient text-xs px-1.5 py-0.5 text-black font-semibold">
                          {count}
                        </Badge>
                      )}
                      
                      {/* Icon Badge */}
                      <div className={`icon-badge ${card.badgeClass}`}>
                        <Icon className="h-5 w-5 md:h-6 md:w-6 text-white" />
                      </div>
                      
                      {/* Card Text */}
                      <div className="space-y-0.5">
                        <h3 className="font-semibold text-sm md:text-base text-foreground group-hover:text-[var(--gold)] transition-colors">
                          {card.title}
                        </h3>
                        <p className="text-xs text-muted-foreground leading-tight hidden sm:block">
                          {card.description}
                        </p>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Account Drawer */}
      <Sheet open={activeDrawer === "account"} onOpenChange={(open) => !open && setActiveDrawer(null)}>
        <SheetContent className="w-[280px] sm:w-[320px] glass-card border-l-0 p-0">
          <SheetHeader className="p-4 pb-3 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="icon-badge icon-badge-blue">
                <User className="h-5 w-5 text-white" />
              </div>
              <div>
                <SheetTitle className="text-base font-semibold">Account</SheetTitle>
                <p className="text-xs text-muted-foreground">Manage your profile</p>
              </div>
            </div>
          </SheetHeader>
          <ScrollArea className="h-[calc(100vh-100px)]">
            <div className="p-4 space-y-4">
              <div className="flex items-center gap-4 p-3 rounded-lg glass-card">
                <div className="w-14 h-14 rounded-full bg-[var(--bronze)]/20 flex items-center justify-center">
                  <User className="h-7 w-7 text-[var(--bronze)]" />
                </div>
                <Button variant="outline" size="sm" className="bg-white/5 border-white/10">
                  Change Avatar
                </Button>
              </div>

              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Display Name</Label>
                <Input placeholder="Your name" defaultValue="User" className="bg-white/5 border-white/10" />
              </div>

              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Email</Label>
                <Input type="email" placeholder="your@email.com" className="bg-white/5 border-white/10" />
              </div>

              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Bio</Label>
                <Input placeholder="Tell us about yourself" className="bg-white/5 border-white/10" />
              </div>

              <Button className="w-full bronze-gradient hover:opacity-90">
                <Save className="h-4 w-4 mr-2" />
                Save Changes
              </Button>

              <div className="pt-4 border-t border-white/10">
                <p className="text-xs text-destructive mb-2">Danger Zone</p>
                <Button variant="destructive" size="sm" className="w-full">
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete Account
                </Button>
              </div>
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>

      {/* Billing Drawer */}
      <Sheet open={activeDrawer === "billing"} onOpenChange={(open) => !open && setActiveDrawer(null)}>
        <SheetContent className="w-[280px] sm:w-[320px] glass-card border-l-0 p-0">
          <SheetHeader className="p-4 pb-3 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="icon-badge icon-badge-green">
                <CreditCard className="h-5 w-5 text-white" />
              </div>
              <div>
                <SheetTitle className="text-base font-semibold">Billing</SheetTitle>
                <p className="text-xs text-muted-foreground">Manage your subscription</p>
              </div>
            </div>
          </SheetHeader>
          <ScrollArea className="h-[calc(100vh-100px)]">
            <div className="p-4 space-y-4">
              {/* Current Plan */}
              <div className="p-4 rounded-lg glass-card border border-[var(--bronze)]/30">
                <p className="text-xs text-muted-foreground mb-1">Current Plan</p>
                <p className="text-lg font-semibold text-[var(--gold)]">Free</p>
                <p className="text-xs text-muted-foreground">50 messages/month</p>
              </div>

              {/* Upgrade Button */}
              <Button 
                className="w-full bronze-gradient hover:opacity-90"
                onClick={() => {
                  setActiveDrawer(null)
                  router.push("/pricing")
                }}
              >
                <ExternalLink className="h-4 w-4 mr-2" />
                Upgrade Plan
              </Button>

              {/* Manage Billing */}
              <Button 
                variant="outline" 
                className="w-full bg-white/5 border-white/10"
                onClick={async () => {
                  try {
                    const response = await fetch("/api/billing/portal", { method: "POST" })
                    const data = await response.json()
                    if (data.url) {
                      window.location.href = data.url
                    }
                  } catch (error) {
                    console.error("Error opening billing portal:", error)
                  }
                }}
              >
                <CreditCard className="h-4 w-4 mr-2" />
                Manage Billing & Invoices
              </Button>

              {/* Usage Info */}
              <div className="pt-4 border-t border-white/10">
                <p className="text-xs text-muted-foreground mb-3">This Period</p>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Messages</span>
                    <span>0 / 50</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Tokens</span>
                    <span>0 / 50K</span>
                  </div>
                </div>
              </div>
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>

      {/* API Keys Drawer */}
      <Sheet open={activeDrawer === "api-keys"} onOpenChange={(open) => !open && setActiveDrawer(null)}>
        <SheetContent className="w-[280px] sm:w-[320px] glass-card border-l-0 p-0">
          <SheetHeader className="p-4 pb-3 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="icon-badge icon-badge-amber">
                <Key className="h-5 w-5 text-white" />
              </div>
              <div>
                <SheetTitle className="text-base font-semibold">API Keys</SheetTitle>
                <p className="text-xs text-muted-foreground">{connectedKeys.length} keys configured</p>
              </div>
            </div>
          </SheetHeader>
          <ScrollArea className="h-[calc(100vh-100px)]">
            <div className="p-4 space-y-2">
              {apiKeys.map((key) => {
                const isConnected = connectedKeys.includes(key.id)
                return (
                  <button
                    key={key.id}
                    onClick={() => toggleKey(key.id)}
                    className={`w-full p-3 rounded-lg border transition-all text-left ${
                      isConnected
                        ? "border-[var(--bronze)] bg-[var(--bronze)]/15"
                        : "border-white/10 hover:border-[var(--bronze)]/50 bg-white/5 hover:bg-white/10"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                          isConnected ? "border-[var(--bronze)] bg-[var(--bronze)]" : "border-muted-foreground/50"
                        }`}
                      >
                        {isConnected && <Check className="h-3 w-3 text-black" />}
                      </div>
                      <div className="flex-1">
                        <span className={`text-sm block ${isConnected ? "text-[var(--gold)]" : ""}`}>
                          {key.label}
                        </span>
                        <span className="text-xs text-muted-foreground">{key.placeholder}</span>
                      </div>
                      {isConnected && (
                        <Badge className="text-xs bg-green-500/20 text-green-400 border-green-500/30">
                          Connected
                        </Badge>
                      )}
                    </div>
                  </button>
                )
              })}
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>

      {/* Connections Drawer */}
      <Sheet open={activeDrawer === "connections"} onOpenChange={(open) => !open && setActiveDrawer(null)}>
        <SheetContent className="w-[280px] sm:w-[320px] glass-card border-l-0 p-0">
          <SheetHeader className="p-4 pb-3 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="icon-badge icon-badge-teal">
                <Link2 className="h-5 w-5 text-white" />
              </div>
              <div>
                <SheetTitle className="text-base font-semibold">Connections</SheetTitle>
                <p className="text-xs text-muted-foreground">{connectedServices.length} services connected</p>
              </div>
            </div>
          </SheetHeader>
          <ScrollArea className="h-[calc(100vh-100px)]">
            <div className="p-4 space-y-2">
              {connections.map((service) => {
                const isConnected = connectedServices.includes(service.id)
                const Icon = service.icon || Link2
                return (
                  <button
                    key={service.id}
                    onClick={() => toggleService(service.id)}
                    className={`w-full p-3 rounded-lg border transition-all text-left ${
                      isConnected
                        ? "border-[var(--bronze)] bg-[var(--bronze)]/15"
                        : "border-white/10 hover:border-[var(--bronze)]/50 bg-white/5 hover:bg-white/10"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                          isConnected ? "border-[var(--bronze)] bg-[var(--bronze)]" : "border-muted-foreground/50"
                        }`}
                      >
                        {isConnected && <Check className="h-3 w-3 text-black" />}
                      </div>
                      <Icon className="h-4 w-4 text-muted-foreground" />
                      <div className="flex-1">
                        <span className={`text-sm block ${isConnected ? "text-[var(--gold)]" : ""}`}>
                          {service.label}
                        </span>
                        <span className="text-xs text-muted-foreground">{service.description}</span>
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>

      {/* Notifications Drawer */}
      <Sheet open={activeDrawer === "notifications"} onOpenChange={(open) => !open && setActiveDrawer(null)}>
        <SheetContent className="w-[280px] sm:w-[320px] glass-card border-l-0 p-0">
          <SheetHeader className="p-4 pb-3 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="icon-badge icon-badge-yellow">
                <Bell className="h-5 w-5 text-white" />
              </div>
              <div>
                <SheetTitle className="text-base font-semibold">Notifications</SheetTitle>
                <p className="text-xs text-muted-foreground">{enabledNotifications.length} enabled</p>
              </div>
            </div>
          </SheetHeader>
          <ScrollArea className="h-[calc(100vh-100px)]">
            <div className="p-4 space-y-2">
              {notificationOptions.map((option) => {
                const isEnabled = enabledNotifications.includes(option.id)
                return (
                  <button
                    key={option.id}
                    onClick={() => toggleNotification(option.id)}
                    className={`w-full p-3 rounded-lg border transition-all text-left ${
                      isEnabled
                        ? "border-[var(--bronze)] bg-[var(--bronze)]/15"
                        : "border-white/10 hover:border-[var(--bronze)]/50 bg-white/5 hover:bg-white/10"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                          isEnabled ? "border-[var(--bronze)] bg-[var(--bronze)]" : "border-muted-foreground/50"
                        }`}
                      >
                        {isEnabled && <Check className="h-3 w-3 text-black" />}
                      </div>
                      <div>
                        <span className={`text-sm block ${isEnabled ? "text-[var(--gold)]" : ""}`}>
                          {option.label}
                        </span>
                        <span className="text-xs text-muted-foreground">{option.description}</span>
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>

      {/* Privacy Drawer */}
      <Sheet open={activeDrawer === "privacy"} onOpenChange={(open) => !open && setActiveDrawer(null)}>
        <SheetContent className="w-[280px] sm:w-[320px] glass-card border-l-0 p-0">
          <SheetHeader className="p-4 pb-3 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="icon-badge icon-badge-pink">
                <Shield className="h-5 w-5 text-white" />
              </div>
              <div>
                <SheetTitle className="text-base font-semibold">Privacy</SheetTitle>
                <p className="text-xs text-muted-foreground">{privacySettings.length} settings enabled</p>
              </div>
            </div>
          </SheetHeader>
          <ScrollArea className="h-[calc(100vh-100px)]">
            <div className="p-4 space-y-2">
              {privacyOptions.map((option) => {
                const isEnabled = privacySettings.includes(option.id)
                return (
                  <button
                    key={option.id}
                    onClick={() => togglePrivacy(option.id)}
                    className={`w-full p-3 rounded-lg border transition-all text-left ${
                      isEnabled
                        ? "border-[var(--bronze)] bg-[var(--bronze)]/15"
                        : "border-white/10 hover:border-[var(--bronze)]/50 bg-white/5 hover:bg-white/10"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                          isEnabled ? "border-[var(--bronze)] bg-[var(--bronze)]" : "border-muted-foreground/50"
                        }`}
                      >
                        {isEnabled && <Check className="h-3 w-3 text-black" />}
                      </div>
                      <div>
                        <span className={`text-sm block ${isEnabled ? "text-[var(--gold)]" : ""}`}>
                          {option.label}
                        </span>
                        <span className="text-xs text-muted-foreground">{option.description}</span>
                      </div>
                    </div>
                  </button>
                )
              })}
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>

      {/* Appearance Drawer */}
      <Sheet open={activeDrawer === "appearance"} onOpenChange={(open) => !open && setActiveDrawer(null)}>
        <SheetContent className="w-[280px] sm:w-[320px] glass-card border-l-0 p-0">
          <SheetHeader className="p-4 pb-3 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="icon-badge icon-badge-orange">
                <Palette className="h-5 w-5 text-white" />
              </div>
              <div>
                <SheetTitle className="text-base font-semibold">Appearance</SheetTitle>
                <p className="text-xs text-muted-foreground">Customize the look</p>
              </div>
            </div>
          </SheetHeader>
          <ScrollArea className="h-[calc(100vh-100px)]">
            <div className="p-4 space-y-4">
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Theme</Label>
                {mounted ? (
                  <div className="flex gap-2">
                    {["light", "dark", "system"].map((themeOption) => (
                      <button
                        key={themeOption}
                        onClick={() => setTheme(themeOption)}
                        className={`flex-1 p-2 rounded-lg border text-sm transition-all ${
                          theme === themeOption
                            ? "border-[var(--bronze)] bg-[var(--bronze)]/15 text-[var(--gold)]"
                            : "border-white/10 hover:border-[var(--bronze)]/50 bg-white/5"
                        }`}
                      >
                        {themeOption.charAt(0).toUpperCase() + themeOption.slice(1)}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="h-10 bg-white/5 animate-pulse rounded-lg" />
                )}
                <p className="text-[10px] text-muted-foreground">
                  Currently: {mounted ? resolvedTheme : "loading..."}
                </p>
              </div>

              <div className="space-y-2">
                {appearanceOptions.map((option) => {
                  const isEnabled = appearanceSettings.includes(option.id)
                  return (
                    <button
                      key={option.id}
                      onClick={() => toggleAppearance(option.id)}
                      className={`w-full p-3 rounded-lg border transition-all text-left ${
                        isEnabled
                          ? "border-[var(--bronze)] bg-[var(--bronze)]/15"
                          : "border-white/10 hover:border-[var(--bronze)]/50 bg-white/5 hover:bg-white/10"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                            isEnabled ? "border-[var(--bronze)] bg-[var(--bronze)]" : "border-muted-foreground/50"
                          }`}
                        >
                          {isEnabled && <Check className="h-3 w-3 text-black" />}
                        </div>
                        <div>
                          <span className={`text-sm block ${isEnabled ? "text-[var(--gold)]" : ""}`}>
                            {option.label}
                          </span>
                          <span className="text-xs text-muted-foreground">{option.description}</span>
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>
    </div>
  )
}
