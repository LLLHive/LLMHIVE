"use client"
import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import { useTheme } from "next-themes"
import { useUser } from "@clerk/nextjs"
import Image from "next/image"
import { LogoText } from "@/components/branding"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { User, Link2, Bell, Shield, Palette, Check, Github, Trash2, Save, CreditCard, ExternalLink, Loader2, BarChart3, Sliders, Target, Zap, Settings2, Lightbulb, CheckCircle, ListTree, GraduationCap, SpellCheck, Boxes, Building2 } from "lucide-react"
import Link from "next/link"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { loadOrchestratorSettings, saveOrchestratorSettings, DEFAULT_ORCHESTRATOR_SETTINGS } from "@/lib/settings-storage"
import type { OrchestratorSettings } from "@/lib/types"
import type { CriteriaSettings } from "@/lib/types"
import { Sidebar } from "@/components/sidebar"
import { UserAccountMenu } from "@/components/user-account-menu"
import { ROUTES } from "@/lib/routes"
import { useAuth } from "@/lib/auth-context"
import { useConversationsContext } from "@/lib/conversations-context"
import { toast } from "@/lib/toast"

// LocalStorage keys for settings persistence
const STORAGE_KEYS = {
  APPEARANCE: "llmhive-appearance-settings",
  NOTIFICATIONS: "llmhive-notification-settings",
  PRIVACY: "llmhive-privacy-settings",
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
  {
    id: "tuning",
    title: "Tuning",
    description: "Accuracy, speed & creativity balance",
    icon: Sliders,
    badgeClass: "icon-badge-cyan",
  },
  {
    id: "advanced",
    title: "Advanced",
    description: "Prompt optimization & AI behavior",
    icon: Settings2,
    badgeClass: "icon-badge-rose",
  },
  {
    id: "models",
    title: "Models",
    description: "Browse and select AI models",
    icon: Boxes,
    badgeClass: "icon-badge-emerald",
    isLink: true,
    href: "/models",
  },
  {
    id: "business-ops",
    title: "Business Ops",
    description: "Trust, billing, org, and integrations hub",
    icon: Building2,
    badgeClass: "icon-badge-bronze",
    isLink: true,
    href: "/business-ops",
  },
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

type DrawerId = "account" | "billing" | "connections" | "notifications" | "privacy" | "appearance" | "tuning" | "advanced" | null

export default function SettingsPage() {
  const router = useRouter()
  const auth = useAuth()
  const { user: clerkUser } = useUser()
  const { 
    conversations, 
    projects, 
    deleteConversation, 
    updateConversation 
  } = useConversationsContext()
  const { theme, setTheme, resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  const [activeDrawer, setActiveDrawer] = useState<DrawerId>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)

  // State for various settings - initialized from localStorage
  const [connectedServices, setConnectedServices] = useState<string[]>([])
  const [enabledNotifications, setEnabledNotifications] = useState<string[]>([])
  const [privacySettings, setPrivacySettings] = useState<string[]>([])
  const [appearanceSettings, setAppearanceSettings] = useState<string[]>([])
  
  // Account form state
  const [displayName, setDisplayName] = useState("")
  const [isSavingAccount, setIsSavingAccount] = useState(false)
  
  // Tuning settings state
  const [criteriaSettings, setCriteriaSettings] = useState<CriteriaSettings>({
    accuracy: 70,
    speed: 70,
    creativity: 50,
  })
  
  // Advanced/Orchestrator settings state
  const [orchestratorSettings, setOrchestratorSettings] = useState<OrchestratorSettings>(DEFAULT_ORCHESTRATOR_SETTINGS)
  
  // Initialize account form with Clerk user data
  useEffect(() => {
    if (clerkUser) {
      setDisplayName(clerkUser.fullName || clerkUser.firstName || "")
    }
  }, [clerkUser])
  
  // Save account changes to Clerk
  const handleSaveAccount = async () => {
    if (!clerkUser) {
      toast.error("You must be signed in to save changes")
      return
    }
    
    setIsSavingAccount(true)
    try {
      // Parse the name into first/last name
      const nameParts = displayName.trim().split(" ")
      const firstName = nameParts[0] || ""
      const lastName = nameParts.slice(1).join(" ") || ""
      
      await clerkUser.update({
        firstName,
        lastName,
      })
      
      toast.success("Account updated successfully!")
    } catch (error) {
      console.error("Failed to update account:", error)
      toast.error("Failed to update account. Please try again.")
    } finally {
      setIsSavingAccount(false)
    }
  }
  
  // Load settings from localStorage on mount
  useEffect(() => {
    setMounted(true)
    
    try {
      const savedAppearance = localStorage.getItem(STORAGE_KEYS.APPEARANCE)
      const savedNotifications = localStorage.getItem(STORAGE_KEYS.NOTIFICATIONS)
      const savedPrivacy = localStorage.getItem(STORAGE_KEYS.PRIVACY)
      const savedConnections = localStorage.getItem(STORAGE_KEYS.CONNECTIONS)
      
      const parsedAppearance = savedAppearance ? JSON.parse(savedAppearance) : ["animations"]
      setAppearanceSettings(parsedAppearance)
      setEnabledNotifications(savedNotifications ? JSON.parse(savedNotifications) : ["email", "updates"])
      setPrivacySettings(savedPrivacy ? JSON.parse(savedPrivacy) : ["shareUsage"])
      setConnectedServices(savedConnections ? JSON.parse(savedConnections) : ["github"])
      
      document.documentElement.classList.toggle('compact-mode', parsedAppearance.includes('compactMode'))
      document.documentElement.classList.toggle('no-animations', !parsedAppearance.includes('animations'))
      
      // Load tuning/criteria settings and orchestrator settings
      const loadedSettings = loadOrchestratorSettings()
      setOrchestratorSettings(loadedSettings)
      if (loadedSettings.criteria) {
        setCriteriaSettings(loadedSettings.criteria)
      }
    } catch (e) {
      console.error("Failed to load settings:", e)
      setAppearanceSettings(["animations"])
      setEnabledNotifications(["email", "updates"])
      setPrivacySettings(["shareUsage"])
      setConnectedServices(["github"])
    }
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

  // Handle criteria/tuning changes
  const handleCriteriaChange = useCallback((newCriteria: CriteriaSettings) => {
    setCriteriaSettings(newCriteria)
    // Save to orchestrator settings
    const currentSettings = loadOrchestratorSettings()
    saveOrchestratorSettings({ ...currentSettings, criteria: newCriteria })
  }, [])

  // Tuning presets
  const tuningPresets = [
    { name: "Balanced", accuracy: 70, speed: 70, creativity: 50 },
    { name: "Fast", accuracy: 50, speed: 100, creativity: 30 },
    { name: "Precise", accuracy: 100, speed: 30, creativity: 40 },
    { name: "Creative", accuracy: 60, speed: 60, creativity: 100 },
  ]

  const getCount = (id: string) => {
    switch (id) {
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
          conversations={conversations.filter((c) => !c.archived)}
          currentConversationId={null}
          onNewChat={() => router.push(ROUTES.HOME)}
          onSelectConversation={(id) => router.push(`${ROUTES.HOME}?chat=${id}`)}
          onDeleteConversation={(id) => deleteConversation(id)}
          onTogglePin={(id) => {
            const conv = conversations.find(c => c.id === id)
            if (conv) updateConversation(id, { pinned: !conv.pinned })
          }}
          onRenameConversation={() => {}}
          onMoveToProject={() => {}}
          projects={projects}
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
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 md:gap-4">
                {settingsCards.map((card, index) => {
                  const Icon = card.icon
                  const count = getCount(card.id)
                  const cardContent = (
                    <>
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
                    </>
                  )
                  
                  // If card has a link, render as Link
                  if ((card as any).isLink && (card as any).href) {
                    return (
                      <Link
                        key={card.id}
                        href={(card as any).href}
                        className="settings-card group llmhive-fade-in"
                        style={{ animationDelay: `${0.1 + index * 0.05}s` }}
                      >
                        {cardContent}
                      </Link>
                    )
                  }
                  
                  return (
                    <button
                      key={card.id}
                      onClick={() => {
                        setActiveDrawer(card.id as DrawerId)
                      }}
                      className="settings-card group llmhive-fade-in"
                      style={{ animationDelay: `${0.1 + index * 0.05}s` }}
                    >
                      {cardContent}
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
                {clerkUser?.imageUrl ? (
                  <img 
                    src={clerkUser.imageUrl} 
                    alt="Profile" 
                    className="w-14 h-14 rounded-full object-cover"
                  />
                ) : (
                  <div className="w-14 h-14 rounded-full bg-[var(--bronze)]/20 flex items-center justify-center">
                    <User className="h-7 w-7 text-[var(--bronze)]" />
                  </div>
                )}
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="bg-white/5 border-white/10"
                  onClick={() => auth.openUserProfile()}
                >
                  Change Avatar
                </Button>
              </div>

              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Display Name</Label>
                <Input 
                  placeholder="Your name" 
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="bg-white/5 border-white/10" 
                />
              </div>

              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Email</Label>
                <Input 
                  type="email" 
                  value={clerkUser?.primaryEmailAddress?.emailAddress || ""}
                  disabled
                  className="bg-white/5 border-white/10 opacity-60 cursor-not-allowed" 
                />
                <p className="text-[10px] text-muted-foreground">Email is managed by your sign-in provider</p>
              </div>

              <Button 
                className="w-full bronze-gradient hover:opacity-90"
                onClick={handleSaveAccount}
                disabled={isSavingAccount || !displayName.trim()}
              >
                {isSavingAccount ? (
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <Save className="h-4 w-4 mr-2" />
                )}
                Save Changes
              </Button>

              <div className="pt-4 border-t border-white/10">
                <p className="text-xs text-muted-foreground mb-2">Advanced Settings</p>
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="w-full bg-white/5 border-white/10"
                  onClick={() => auth.openUserProfile()}
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Manage Account in Clerk
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
                <p className="text-xs text-muted-foreground">Forever free with multi-model orchestration</p>
              </div>

              {/* FREE Tier Marketing */}
              <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/30">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-5 h-5 rounded-full bg-green-500 flex items-center justify-center">
                    <Check className="h-3 w-3 text-white" />
                  </div>
                  <span className="text-sm font-semibold text-green-400">FREE tier BEATS most paid models</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Our patented multi-model orchestration delivers exceptional quality at no cost.
                </p>
              </div>

              {/* Upgrade Button */}
              <Button 
                className="w-full bronze-gradient hover:opacity-90"
                onClick={() => {
                  setActiveDrawer(null)
                  router.push("/pricing")
                }}
              >
                <Zap className="h-4 w-4 mr-2" />
                Upgrade to ELITE (#1 in ALL Categories)
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
                    <span className="text-muted-foreground">Orchestration</span>
                    <span className="text-green-400">FREE</span>
                  </div>
                </div>
              </div>

              {/* Pricing Tiers Summary */}
              <div className="pt-4 border-t border-white/10">
                <p className="text-xs text-muted-foreground mb-3">Available Plans</p>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-green-400 font-medium">Free</span>
                    <span className="text-muted-foreground">$0/mo</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Lite</span>
                    <span className="text-muted-foreground">$14.99/mo</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[var(--bronze)] font-medium">Pro</span>
                    <span className="text-muted-foreground">$29.99/mo</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Enterprise</span>
                    <span className="text-muted-foreground">$35/seat</span>
                  </div>
                </div>
              </div>
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

      {/* Tuning Drawer */}
      <Sheet open={activeDrawer === "tuning"} onOpenChange={(open) => !open && setActiveDrawer(null)}>
        <SheetContent className="w-[320px] sm:w-[380px] glass-card border-l-0 p-0">
          <SheetHeader className="p-4 pb-3 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="icon-badge icon-badge-cyan">
                <Sliders className="h-5 w-5 text-white" />
              </div>
              <div>
                <SheetTitle className="text-base font-semibold">Tuning</SheetTitle>
                <p className="text-xs text-muted-foreground">Balance accuracy, speed & creativity</p>
              </div>
            </div>
          </SheetHeader>
          <ScrollArea className="h-[calc(100vh-100px)]">
            <div className="p-4 space-y-6">
              {/* Description */}
              <div className="p-3 rounded-lg glass-card border border-[var(--bronze)]/20">
                <h4 className="font-semibold text-sm mb-1 text-[var(--gold)]">Dynamic Criteria Equalizer</h4>
                <p className="text-xs text-muted-foreground">
                  Adjust how the AI hive balances accuracy, speed, and creativity for your responses.
                </p>
              </div>

              {/* Presets */}
              <div className="space-y-2">
                <Label className="text-xs text-muted-foreground">Quick Presets</Label>
                <div className="grid grid-cols-4 gap-2">
                  {tuningPresets.map((preset) => {
                    const isActive = 
                      criteriaSettings.accuracy === preset.accuracy &&
                      criteriaSettings.speed === preset.speed &&
                      criteriaSettings.creativity === preset.creativity
                    return (
                      <Button
                        key={preset.name}
                        variant="outline"
                        size="sm"
                        className={`text-xs h-auto py-2 ${
                          isActive 
                            ? "border-[var(--bronze)] bg-[var(--bronze)]/15 text-[var(--gold)]" 
                            : "bg-white/5 border-white/10"
                        }`}
                        onClick={() => handleCriteriaChange(preset)}
                      >
                        {preset.name}
                      </Button>
                    )
                  })}
                </div>
              </div>

              {/* Accuracy Slider */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
                      <Target className="h-4 w-4 text-blue-500" />
                    </div>
                    <div>
                      <span className="text-sm font-medium">Accuracy</span>
                      <p className="text-[10px] text-muted-foreground">Higher = more verification</p>
                    </div>
                  </div>
                  <span className="text-sm font-bold text-blue-500">{criteriaSettings.accuracy}%</span>
                </div>
                <Slider
                  value={[criteriaSettings.accuracy]}
                  onValueChange={([value]) => handleCriteriaChange({ ...criteriaSettings, accuracy: value })}
                  max={100}
                  step={10}
                  className="[&_[role=slider]]:bg-blue-500 [&_[role=slider]]:border-blue-500"
                />
              </div>

              {/* Speed Slider */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-green-500/20 flex items-center justify-center">
                      <Zap className="h-4 w-4 text-green-500" />
                    </div>
                    <div>
                      <span className="text-sm font-medium">Speed</span>
                      <p className="text-[10px] text-muted-foreground">Higher = faster responses</p>
                    </div>
                  </div>
                  <span className="text-sm font-bold text-green-500">{criteriaSettings.speed}%</span>
                </div>
                <Slider
                  value={[criteriaSettings.speed]}
                  onValueChange={([value]) => handleCriteriaChange({ ...criteriaSettings, speed: value })}
                  max={100}
                  step={10}
                  className="[&_[role=slider]]:bg-green-500 [&_[role=slider]]:border-green-500"
                />
              </div>

              {/* Creativity Slider */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
                      <Palette className="h-4 w-4 text-purple-500" />
                    </div>
                    <div>
                      <span className="text-sm font-medium">Creativity</span>
                      <p className="text-[10px] text-muted-foreground">Higher = more inventive</p>
                    </div>
                  </div>
                  <span className="text-sm font-bold text-purple-500">{criteriaSettings.creativity}%</span>
                </div>
                <Slider
                  value={[criteriaSettings.creativity]}
                  onValueChange={([value]) => handleCriteriaChange({ ...criteriaSettings, creativity: value })}
                  max={100}
                  step={10}
                  className="[&_[role=slider]]:bg-purple-500 [&_[role=slider]]:border-purple-500"
                />
              </div>

              {/* Current Settings Summary */}
              <div className="pt-4 border-t border-white/10">
                <p className="text-xs text-muted-foreground mb-2">Current Configuration</p>
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20">
                    <span className="text-lg font-bold text-blue-500">{criteriaSettings.accuracy}%</span>
                    <p className="text-[10px] text-muted-foreground">Accuracy</p>
                  </div>
                  <div className="p-2 rounded-lg bg-green-500/10 border border-green-500/20">
                    <span className="text-lg font-bold text-green-500">{criteriaSettings.speed}%</span>
                    <p className="text-[10px] text-muted-foreground">Speed</p>
                  </div>
                  <div className="p-2 rounded-lg bg-purple-500/10 border border-purple-500/20">
                    <span className="text-lg font-bold text-purple-500">{criteriaSettings.creativity}%</span>
                    <p className="text-[10px] text-muted-foreground">Creativity</p>
                  </div>
                </div>
              </div>
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>

      {/* Advanced Drawer */}
      <Sheet open={activeDrawer === "advanced"} onOpenChange={(open) => !open && setActiveDrawer(null)}>
        <SheetContent className="w-[320px] sm:w-[380px] glass-card border-l-0 p-0">
          <SheetHeader className="p-4 pb-3 border-b border-white/10">
            <div className="flex items-center gap-3">
              <div className="icon-badge icon-badge-rose">
                <Settings2 className="h-5 w-5 text-white" />
              </div>
              <div>
                <SheetTitle className="text-lg font-semibold">Advanced Tuning</SheetTitle>
                <p className="text-xs text-muted-foreground">Fine-tune orchestration behavior</p>
              </div>
            </div>
          </SheetHeader>
          <ScrollArea className="h-[calc(100vh-100px)]">
            <div className="p-4 space-y-4">
              {/* Prompt Optimization */}
              <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/30 border border-white/5">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
                    <Lightbulb className="h-5 w-5 text-amber-500" />
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Prompt Optimization</Label>
                    <p className="text-[10px] text-muted-foreground">Enhance prompts for better results</p>
                  </div>
                </div>
                <Switch
                  checked={orchestratorSettings.promptOptimization !== false}
                  onCheckedChange={(checked) => {
                    const newSettings = { ...orchestratorSettings, promptOptimization: checked }
                    setOrchestratorSettings(newSettings)
                    saveOrchestratorSettings(newSettings)
                    toast.success("Prompt Optimization " + (checked ? "enabled" : "disabled"))
                  }}
                  className="data-[state=checked]:bg-[var(--bronze)]"
                />
              </div>

              {/* Output Validation */}
              <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/30 border border-white/5">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Output Validation</Label>
                    <p className="text-[10px] text-muted-foreground">Verify and fact-check responses</p>
                  </div>
                </div>
                <Switch
                  checked={orchestratorSettings.outputValidation !== false}
                  onCheckedChange={(checked) => {
                    const newSettings = { ...orchestratorSettings, outputValidation: checked }
                    setOrchestratorSettings(newSettings)
                    saveOrchestratorSettings(newSettings)
                    toast.success("Output Validation " + (checked ? "enabled" : "disabled"))
                  }}
                  className="data-[state=checked]:bg-[var(--bronze)]"
                />
              </div>

              {/* Answer Structure */}
              <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/30 border border-white/5">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-blue-500/20 flex items-center justify-center">
                    <ListTree className="h-5 w-5 text-blue-500" />
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Answer Structure</Label>
                    <p className="text-[10px] text-muted-foreground">Format with clear sections</p>
                  </div>
                </div>
                <Switch
                  checked={orchestratorSettings.answerStructure !== false}
                  onCheckedChange={(checked) => {
                    const newSettings = { ...orchestratorSettings, answerStructure: checked }
                    setOrchestratorSettings(newSettings)
                    saveOrchestratorSettings(newSettings)
                    toast.success("Answer Structure " + (checked ? "enabled" : "disabled"))
                  }}
                  className="data-[state=checked]:bg-[var(--bronze)]"
                />
              </div>

              {/* Learn from Chat */}
              <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/30 border border-white/5">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-purple-500/20 flex items-center justify-center">
                    <GraduationCap className="h-5 w-5 text-purple-500" />
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Learn from Chat</Label>
                    <p className="text-[10px] text-muted-foreground">Improve based on conversation</p>
                  </div>
                </div>
                <Switch
                  checked={orchestratorSettings.learnFromChat !== false}
                  onCheckedChange={(checked) => {
                    const newSettings = { ...orchestratorSettings, learnFromChat: checked }
                    setOrchestratorSettings(newSettings)
                    saveOrchestratorSettings(newSettings)
                    toast.success("Learn from Chat " + (checked ? "enabled" : "disabled"))
                  }}
                  className="data-[state=checked]:bg-[var(--bronze)]"
                />
              </div>

              {/* Spell Check */}
              <div className="flex items-center justify-between p-3 rounded-lg bg-secondary/30 border border-white/5">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-cyan-500/20 flex items-center justify-center">
                    <SpellCheck className="h-5 w-5 text-cyan-500" />
                  </div>
                  <div>
                    <Label className="text-sm font-medium">Spell Check</Label>
                    <p className="text-[10px] text-muted-foreground">Auto-correct spelling in prompts</p>
                  </div>
                </div>
                <Switch
                  checked={orchestratorSettings.enableSpellCheck !== false}
                  onCheckedChange={(checked) => {
                    const newSettings = { ...orchestratorSettings, enableSpellCheck: checked }
                    setOrchestratorSettings(newSettings)
                    saveOrchestratorSettings(newSettings)
                    toast.success("Spell Check " + (checked ? "enabled" : "disabled"))
                  }}
                  className="data-[state=checked]:bg-[var(--bronze)]"
                />
              </div>

              {/* Info Footer */}
              <div className="pt-4 border-t border-white/10">
                <p className="text-xs text-muted-foreground text-center">
                  These settings are applied automatically to all chats
                </p>
              </div>
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>
    </div>
  )
}
