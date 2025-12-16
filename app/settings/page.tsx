"use client"
import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import { useTheme } from "next-themes"
import Image from "next/image"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { User, Key, Link2, Bell, Shield, Palette, Check, Github, Trash2, Save } from "lucide-react"
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

// Card data matching home page template card style exactly
const settingsCards = [
  {
    id: "account",
    title: "Account",
    description: "Manage your profile and account details",
    icon: User,
    color: "from-blue-500 to-cyan-500",
  },
  {
    id: "api-keys",
    title: "API Keys",
    description: "Configure external service API keys",
    icon: Key,
    color: "from-purple-500 to-indigo-500",
  },
  {
    id: "connections",
    title: "Connections",
    description: "GitHub, Google, Slack integrations",
    icon: Link2,
    color: "from-emerald-500 to-teal-500",
  },
  {
    id: "notifications",
    title: "Notifications",
    description: "Email, push, and update preferences",
    icon: Bell,
    color: "from-orange-500 to-amber-500",
  },
  {
    id: "privacy",
    title: "Privacy",
    description: "Data sharing and usage controls",
    icon: Shield,
    color: "from-rose-500 to-pink-500",
  },
  {
    id: "appearance",
    title: "Appearance",
    description: "Theme, display, and accessibility",
    icon: Palette,
    color: "from-amber-500 to-yellow-500",
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

type DrawerId = "account" | "api-keys" | "connections" | "notifications" | "privacy" | "appearance" | null

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
    
    // Load all settings from localStorage
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
      
      // Apply appearance settings on load
      document.documentElement.classList.toggle('compact-mode', parsedAppearance.includes('compactMode'))
      document.documentElement.classList.toggle('no-animations', !parsedAppearance.includes('animations'))
    } catch (e) {
      console.error("Failed to load settings:", e)
      // Fallback to defaults
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
      
      // Actually apply appearance settings
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
      case "api-keys":
        return connectedKeys.length
      case "connections":
        return connectedServices.length
      case "notifications":
        return enabledNotifications.length
      case "privacy":
        return privacySettings.length
      case "appearance":
        return appearanceSettings.length
      default:
        return 0
    }
  }

  return (
    <div className="flex h-screen bg-background text-foreground overflow-hidden">
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

      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        <div className="hidden md:flex items-center justify-end p-3 border-b border-border bg-card/50">
          <UserAccountMenu />
        </div>

        <div className="flex-1 h-full overflow-auto">
          <div className="min-h-full flex flex-col items-center justify-start px-4 pt-0 pb-20">
            <div className="text-center mb-0">
              <div className="relative w-40 h-40 md:w-[280px] md:h-[280px] lg:w-[320px] lg:h-[320px] mx-auto mb-0 -mt-4 md:-mt-8 lg:-mt-10">
                <Image src="/logo.png" alt="LLMHive" fill className="object-contain" priority />
              </div>
              <h1 className="-mt-6 md:-mt-8 lg:-mt-10 text-[1.75rem] md:text-[2.85rem] lg:text-[3.4rem] font-bold mb-1 bg-gradient-to-r from-[var(--bronze)] via-[var(--gold)] to-[var(--bronze)] bg-clip-text text-transparent">
                Settings
              </h1>
              <p className="text-muted-foreground text-sm md:text-base max-w-md mx-auto mb-0">
                Configure your account, integrations, and preferences
              </p>
            </div>

            <div className="w-16 h-px bg-border my-2" />

            <div className="w-full max-w-5xl">
              <p className="text-sm text-muted-foreground text-center mb-2">Select a category to configure</p>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
                {settingsCards.map((card) => {
                  const Icon = card.icon
                  const count = getCount(card.id)
                  return (
                    <button
                      key={card.id}
                      onClick={() => setActiveDrawer(card.id as DrawerId)}
                      className="group relative p-4 md:p-5 rounded-xl border border-border bg-card hover:bg-secondary/50 transition-all duration-300 hover:border-[var(--bronze)]/50 hover:shadow-lg hover:shadow-[var(--bronze)]/5 text-left"
                    >
                      {count > 0 && (
                        <Badge className="absolute top-2 right-2 bronze-gradient text-white text-xs px-1.5 py-0.5">
                          {count}
                        </Badge>
                      )}
                      <div
                        className={`w-10 h-10 md:w-12 md:h-12 rounded-lg bg-gradient-to-br ${card.color} flex items-center justify-center mb-3 group-hover:scale-110 transition-transform duration-300`}
                      >
                        <Icon className="h-5 w-5 md:h-6 md:w-6 text-white" />
                      </div>
                      <h3 className="font-semibold text-sm md:text-base mb-1 group-hover:text-[var(--bronze)] transition-colors">
                        {card.title}
                      </h3>
                      <p className="text-xs md:text-sm text-muted-foreground">{card.description}</p>
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
        <SheetContent className="w-[260px] sm:w-[280px] bg-card/95 backdrop-blur-xl border-l border-border p-0">
          <SheetHeader className="p-4 pb-3 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center">
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
              <div className="flex items-center gap-4 p-3 rounded-lg border border-border">
                <div className="w-14 h-14 rounded-full bg-[var(--bronze)]/20 flex items-center justify-center">
                  <User className="h-7 w-7 text-[var(--bronze)]" />
                </div>
                <Button variant="outline" size="sm">
                  Change Avatar
                </Button>
              </div>

              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Display Name</Label>
                <Input placeholder="Your name" defaultValue="User" className="bg-secondary/50 border-border" />
              </div>

              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Email</Label>
                <Input type="email" placeholder="your@email.com" className="bg-secondary/50 border-border" />
              </div>

              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Bio</Label>
                <Input placeholder="Tell us about yourself" className="bg-secondary/50 border-border" />
              </div>

              <Button className="w-full bronze-gradient hover:opacity-90">
                <Save className="h-4 w-4 mr-2" />
                Save Changes
              </Button>

              <div className="pt-4 border-t border-border">
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

      {/* API Keys Drawer */}
      <Sheet open={activeDrawer === "api-keys"} onOpenChange={(open) => !open && setActiveDrawer(null)}>
        <SheetContent className="w-[260px] sm:w-[280px] bg-card/95 backdrop-blur-xl border-l border-border p-0">
          <SheetHeader className="p-4 pb-3 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-indigo-500 flex items-center justify-center">
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
                        ? "border-[var(--bronze)] bg-[var(--bronze)]/10"
                        : "border-border hover:border-[var(--bronze)]/50 hover:bg-secondary/50"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                          isConnected ? "border-[var(--bronze)] bg-[var(--bronze)]" : "border-muted-foreground/50"
                        }`}
                      >
                        {isConnected && <Check className="h-3 w-3 text-white" />}
                      </div>
                      <div className="flex-1">
                        <span className={`text-sm block ${isConnected ? "text-[var(--bronze)]" : ""}`}>
                          {key.label}
                        </span>
                        <span className="text-xs text-muted-foreground">{key.placeholder}</span>
                      </div>
                      {isConnected && (
                        <Badge variant="secondary" className="text-xs bg-green-500/10 text-green-500">
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
        <SheetContent className="w-[260px] sm:w-[280px] bg-card/95 backdrop-blur-xl border-l border-border p-0">
          <SheetHeader className="p-4 pb-3 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-500 flex items-center justify-center">
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
                        ? "border-[var(--bronze)] bg-[var(--bronze)]/10"
                        : "border-border hover:border-[var(--bronze)]/50 hover:bg-secondary/50"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                          isConnected ? "border-[var(--bronze)] bg-[var(--bronze)]" : "border-muted-foreground/50"
                        }`}
                      >
                        {isConnected && <Check className="h-3 w-3 text-white" />}
                      </div>
                      <Icon className="h-4 w-4 text-muted-foreground" />
                      <div className="flex-1">
                        <span className={`text-sm block ${isConnected ? "text-[var(--bronze)]" : ""}`}>
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
        <SheetContent className="w-[260px] sm:w-[280px] bg-card/95 backdrop-blur-xl border-l border-border p-0">
          <SheetHeader className="p-4 pb-3 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-orange-500 to-amber-500 flex items-center justify-center">
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
                        ? "border-[var(--bronze)] bg-[var(--bronze)]/10"
                        : "border-border hover:border-[var(--bronze)]/50 hover:bg-secondary/50"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                          isEnabled ? "border-[var(--bronze)] bg-[var(--bronze)]" : "border-muted-foreground/50"
                        }`}
                      >
                        {isEnabled && <Check className="h-3 w-3 text-white" />}
                      </div>
                      <div>
                        <span className={`text-sm block ${isEnabled ? "text-[var(--bronze)]" : ""}`}>
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
        <SheetContent className="w-[260px] sm:w-[280px] bg-card/95 backdrop-blur-xl border-l border-border p-0">
          <SheetHeader className="p-4 pb-3 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-rose-500 to-pink-500 flex items-center justify-center">
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
                        ? "border-[var(--bronze)] bg-[var(--bronze)]/10"
                        : "border-border hover:border-[var(--bronze)]/50 hover:bg-secondary/50"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                          isEnabled ? "border-[var(--bronze)] bg-[var(--bronze)]" : "border-muted-foreground/50"
                        }`}
                      >
                        {isEnabled && <Check className="h-3 w-3 text-white" />}
                      </div>
                      <div>
                        <span className={`text-sm block ${isEnabled ? "text-[var(--bronze)]" : ""}`}>
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
        <SheetContent className="w-[260px] sm:w-[280px] bg-card/95 backdrop-blur-xl border-l border-border p-0">
          <SheetHeader className="p-4 pb-3 border-b border-border">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-amber-500 to-yellow-500 flex items-center justify-center">
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
                          ? "border-[var(--bronze)] bg-[var(--bronze)]/10 text-[var(--bronze)]"
                          : "border-border hover:border-[var(--bronze)]/50"
                      }`}
                    >
                        {themeOption.charAt(0).toUpperCase() + themeOption.slice(1)}
                    </button>
                  ))}
                </div>
                ) : (
                  <div className="h-10 bg-secondary/50 animate-pulse rounded-lg" />
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
                          ? "border-[var(--bronze)] bg-[var(--bronze)]/10"
                          : "border-border hover:border-[var(--bronze)]/50 hover:bg-secondary/50"
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-5 h-5 rounded border-2 flex items-center justify-center transition-all ${
                            isEnabled ? "border-[var(--bronze)] bg-[var(--bronze)]" : "border-muted-foreground/50"
                          }`}
                        >
                          {isEnabled && <Check className="h-3 w-3 text-white" />}
                        </div>
                        <div>
                          <span className={`text-sm block ${isEnabled ? "text-[var(--bronze)]" : ""}`}>
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
