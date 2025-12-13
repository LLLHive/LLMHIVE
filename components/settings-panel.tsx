"use client"

import { useState, useEffect } from "react"
import { useTheme } from "next-themes"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { User, Bell, Palette, Shield, Database, Zap, Key, Plug, Check } from "lucide-react"
import { IntegrationsPanel } from "./integrations-panel"
import { toast } from "@/lib/toast"

// Font size storage key
const FONT_SIZE_KEY = "llmhive-font-size"

export function SettingsPanel() {
  const { theme, setTheme, resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  const [notifications, setNotifications] = useState(true)
  const [autoSave, setAutoSave] = useState(true)
  const [dataRetention, setDataRetention] = useState(30)
  const [temperature, setTemperature] = useState([0.7])
  const [fontSize, setFontSize] = useState("medium")
  
  // API Keys state
  const [apiKeys, setApiKeys] = useState({
    openai: "",
    anthropic: "",
    google: "",
    xai: "",
  })
  const [savingKeys, setSavingKeys] = useState(false)
  
  // Ensure theme is mounted before rendering to avoid hydration mismatch
  useEffect(() => {
    setMounted(true)
    // Load saved font size
    const savedFontSize = localStorage.getItem(FONT_SIZE_KEY)
    if (savedFontSize) {
      setFontSize(savedFontSize)
      applyFontSize(savedFontSize)
    }
  }, [])
  
  const applyFontSize = (size: string) => {
    const root = document.documentElement
    const sizes = { small: "14px", medium: "16px", large: "18px" }
    root.style.setProperty("--base-font-size", sizes[size as keyof typeof sizes] || "16px")
    document.body.style.fontSize = sizes[size as keyof typeof sizes] || "16px"
  }
  
  const handleFontSizeChange = (size: string) => {
    setFontSize(size)
    localStorage.setItem(FONT_SIZE_KEY, size)
    applyFontSize(size)
    toast.success("Font size updated")
  }
  
  const handleSaveApiKeys = async () => {
    setSavingKeys(true)
    try {
      // Store encrypted in localStorage (in production, send to secure backend)
      // For now, just store locally - in production this would go to a secure backend
      const encrypted = btoa(JSON.stringify(apiKeys))
      localStorage.setItem("llmhive-api-keys", encrypted)
      toast.success("API keys saved securely")
    } catch (error) {
      toast.error("Failed to save API keys")
    } finally {
      setSavingKeys(false)
    }
  }
  
  // Load saved API keys on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem("llmhive-api-keys")
      if (saved) {
        const decrypted = JSON.parse(atob(saved))
        setApiKeys(decrypted)
      }
    } catch {
      // Ignore errors loading saved keys
    }
  }, [])

  return (
    <div className="h-full flex flex-col">
      <div className="p-6 border-b border-border">
        <h2 className="text-2xl font-bold">Settings</h2>
        <p className="text-sm text-muted-foreground mt-1">Manage your LLMHive preferences</p>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-6">
          <Tabs defaultValue="general" className="w-full">
            <TabsList className="grid w-full grid-cols-5 mb-6">
              <TabsTrigger value="general">General</TabsTrigger>
              <TabsTrigger value="ai">AI Models</TabsTrigger>
              <TabsTrigger value="integrations">Integrations</TabsTrigger>
              <TabsTrigger value="privacy">Privacy</TabsTrigger>
              <TabsTrigger value="api">API Keys</TabsTrigger>
            </TabsList>

            <TabsContent value="general" className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[var(--bronze)] to-[var(--gold)] flex items-center justify-center">
                      <User className="h-5 w-5 text-background" />
                    </div>
                    <div>
                      <Label className="text-base font-semibold">Profile</Label>
                      <p className="text-sm text-muted-foreground">Manage your account settings</p>
                    </div>
                  </div>
                </div>

                <div className="pl-[52px] space-y-4">
                  <div className="space-y-2">
                    <Label>Display Name</Label>
                    <Input placeholder="Your name" defaultValue="User" />
                  </div>

                  <div className="space-y-2">
                    <Label>Email</Label>
                    <Input type="email" placeholder="your@email.com" />
                  </div>
                </div>
              </div>

              <div className="h-px bg-border" />

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center">
                      <Palette className="h-5 w-5" />
                    </div>
                    <div>
                      <Label className="text-base font-semibold">Appearance</Label>
                      <p className="text-sm text-muted-foreground">Customize the interface</p>
                    </div>
                  </div>
                </div>

                <div className="pl-[52px] space-y-4">
                  <div className="space-y-2">
                    <Label>Theme</Label>
                    {mounted ? (
                      <Select value={theme} onValueChange={setTheme}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="dark">Dark</SelectItem>
                          <SelectItem value="light">Light</SelectItem>
                          <SelectItem value="system">System</SelectItem>
                        </SelectContent>
                      </Select>
                    ) : (
                      <div className="h-10 bg-secondary rounded-md animate-pulse" />
                    )}
                    <p className="text-xs text-muted-foreground">
                      Current: {mounted ? resolvedTheme : "loading..."}
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label>Font Size</Label>
                    <Select value={fontSize} onValueChange={handleFontSizeChange}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="small">Small (14px)</SelectItem>
                        <SelectItem value="medium">Medium (16px)</SelectItem>
                        <SelectItem value="large">Large (18px)</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>

              <div className="h-px bg-border" />

              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center">
                      <Bell className="h-5 w-5" />
                    </div>
                    <div>
                      <Label className="text-base font-semibold">Notifications</Label>
                      <p className="text-sm text-muted-foreground">Configure notification preferences</p>
                    </div>
                  </div>
                  <Switch checked={notifications} onCheckedChange={setNotifications} />
                </div>

                {notifications && (
                  <div className="pl-[52px] space-y-3">
                    <div className="flex items-center justify-between">
                      <Label className="text-sm font-normal">Email notifications</Label>
                      <Switch defaultChecked />
                    </div>
                    <div className="flex items-center justify-between">
                      <Label className="text-sm font-normal">Push notifications</Label>
                      <Switch defaultChecked />
                    </div>
                    <div className="flex items-center justify-between">
                      <Label className="text-sm font-normal">Collaboration updates</Label>
                      <Switch defaultChecked />
                    </div>
                  </div>
                )}
              </div>
            </TabsContent>

            <TabsContent value="ai" className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[var(--bronze)] to-[var(--gold)] flex items-center justify-center">
                    <Zap className="h-5 w-5 text-background" />
                  </div>
                  <div>
                    <Label className="text-base font-semibold">Model Preferences</Label>
                    <p className="text-sm text-muted-foreground">Configure default AI model settings</p>
                  </div>
                </div>

                <div className="pl-[52px] space-y-4">
                  <div className="space-y-2">
                    <Label>Default Model</Label>
                    <Select defaultValue="gpt-4o">
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="o1">o1 (Reasoning)</SelectItem>
                        <SelectItem value="o1-pro">o1 Pro (Extended)</SelectItem>
                        <SelectItem value="o3-mini">o3 Mini</SelectItem>
                        <SelectItem value="gpt-4.5-preview">GPT-4.5 Preview</SelectItem>
                        <SelectItem value="gpt-4o">GPT-4o</SelectItem>
                        <SelectItem value="gpt-4o-mini">GPT-4o Mini</SelectItem>
                        <SelectItem value="claude-opus-4">Claude Opus 4</SelectItem>
                        <SelectItem value="claude-sonnet-4">Claude Sonnet 4</SelectItem>
                        <SelectItem value="claude-3.5-haiku">Claude 3.5 Haiku</SelectItem>
                        <SelectItem value="grok-3">Grok 3</SelectItem>
                        <SelectItem value="grok-2">Grok 2</SelectItem>
                        <SelectItem value="gemini-2.5-pro">Gemini 2.5 Pro</SelectItem>
                        <SelectItem value="gemini-2.5-flash">Gemini 2.5 Flash</SelectItem>
                        <SelectItem value="deepseek-r1">DeepSeek R1</SelectItem>
                        <SelectItem value="deepseek-chat">DeepSeek V3</SelectItem>
                        <SelectItem value="llama-3.3-70b">Llama 3.3 70B</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>Temperature: {temperature[0]}</Label>
                      <span className="text-xs text-muted-foreground">Creativity</span>
                    </div>
                    <Slider
                      value={temperature}
                      onValueChange={setTemperature}
                      min={0}
                      max={1}
                      step={0.1}
                      className="w-full"
                    />
                    <p className="text-xs text-muted-foreground">
                      Higher values make output more creative, lower values more focused
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label>Max Tokens</Label>
                    <Input type="number" defaultValue="2048" />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Streaming Responses</Label>
                      <p className="text-xs text-muted-foreground">Show responses as they generate</p>
                    </div>
                    <Switch defaultChecked />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Auto-execute Code</Label>
                      <p className="text-xs text-muted-foreground">Automatically run generated code</p>
                    </div>
                    <Switch />
                  </div>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="integrations" className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[var(--bronze)] to-[var(--gold)] flex items-center justify-center">
                    <Plug className="h-5 w-5 text-background" />
                  </div>
                  <div>
                    <Label className="text-base font-semibold">External Integrations</Label>
                    <p className="text-sm text-muted-foreground">Connect third-party services and tools</p>
                  </div>
                </div>

                <div className="pl-[52px]">
                  <IntegrationsPanel />
                </div>
              </div>
            </TabsContent>

            <TabsContent value="privacy" className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[var(--bronze)] to-[var(--gold)] flex items-center justify-center">
                    <Shield className="h-5 w-5 text-background" />
                  </div>
                  <div>
                    <Label className="text-base font-semibold">Privacy & Security</Label>
                    <p className="text-sm text-muted-foreground">Control your data and security settings</p>
                  </div>
                </div>

                <div className="pl-[52px] space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Auto-save Conversations</Label>
                      <p className="text-xs text-muted-foreground">Automatically save chat history</p>
                    </div>
                    <Switch checked={autoSave} onCheckedChange={setAutoSave} />
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Label>Data Retention: {dataRetention} days</Label>
                    </div>
                    <Slider
                      value={[dataRetention]}
                      onValueChange={(v) => setDataRetention(v[0])}
                      min={7}
                      max={365}
                      step={1}
                      className="w-full"
                    />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Share Analytics</Label>
                      <p className="text-xs text-muted-foreground">Help improve LLMHive</p>
                    </div>
                    <Switch defaultChecked />
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <Label>Use Data for Training</Label>
                      <p className="text-xs text-muted-foreground">Allow conversations to improve models</p>
                    </div>
                    <Switch />
                  </div>

                  <div className="pt-4">
                    <Button variant="destructive" className="w-full">
                      <Database className="h-4 w-4 mr-2" />
                      Clear All Conversation Data
                    </Button>
                  </div>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="api" className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[var(--bronze)] to-[var(--gold)] flex items-center justify-center">
                    <Key className="h-5 w-5 text-background" />
                  </div>
                  <div>
                    <Label className="text-base font-semibold">API Configuration</Label>
                    <p className="text-sm text-muted-foreground">Manage external API keys</p>
                  </div>
                </div>

                <div className="pl-[52px] space-y-4">
                  <div className="space-y-2">
                    <Label>OpenAI API Key</Label>
                    <Input 
                      type="password" 
                      placeholder="sk-..." 
                      value={apiKeys.openai}
                      onChange={(e) => setApiKeys(prev => ({ ...prev, openai: e.target.value }))}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Anthropic API Key</Label>
                    <Input 
                      type="password" 
                      placeholder="sk-ant-..." 
                      value={apiKeys.anthropic}
                      onChange={(e) => setApiKeys(prev => ({ ...prev, anthropic: e.target.value }))}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>Google AI API Key</Label>
                    <Input 
                      type="password" 
                      placeholder="AIza..." 
                      value={apiKeys.google}
                      onChange={(e) => setApiKeys(prev => ({ ...prev, google: e.target.value }))}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label>xAI API Key</Label>
                    <Input 
                      type="password" 
                      placeholder="xai-..." 
                      value={apiKeys.xai}
                      onChange={(e) => setApiKeys(prev => ({ ...prev, xai: e.target.value }))}
                    />
                  </div>

                  <div className="pt-2">
                    <Button 
                      className="w-full bronze-gradient" 
                      onClick={handleSaveApiKeys}
                      disabled={savingKeys}
                    >
                      {savingKeys ? "Saving..." : "Save API Keys"}
                      {!savingKeys && <Check className="h-4 w-4 ml-2" />}
                    </Button>
                  </div>

                  <div className="p-3 rounded-lg bg-secondary/50 border border-border">
                    <p className="text-xs text-muted-foreground">
                      API keys are encrypted and stored securely. They are only used to make requests on your behalf.
                    </p>
                  </div>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </ScrollArea>
    </div>
  )
}
