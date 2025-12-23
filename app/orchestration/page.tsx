"use client"
import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Image from "next/image"
import { LogoText } from "@/components/branding"
import Link from "next/link"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Cpu, Brain, Sliders, Wrench, Hammer, Layers, Check, ExternalLink, Sparkles, Zap, Crown, Target, Shield, Plus, ArrowRight, ArrowLeft, ChevronRight, Code, FlaskConical, Heart, Scale, Megaphone, Search, MessageSquare, Users, Landmark, GraduationCap, BarChart3, Languages, Image as ImageIcon, Wrench as ToolIcon, Loader2 } from "lucide-react"
import { AVAILABLE_MODELS, getModelLogo } from "@/lib/models"
import { REASONING_METHODS, REASONING_CATEGORIES } from "@/lib/reasoning-methods"
import { Sidebar } from "@/components/sidebar"
import { UserAccountMenu } from "@/components/user-account-menu"
import { loadOrchestratorSettings, saveOrchestratorSettings } from "@/lib/settings-storage"
import { ROUTES } from "@/lib/routes"
import { useAuth } from "@/lib/auth-context"
import { STORAGE_KEYS, type SelectedModelConfig, type UserTier, TIER_CONFIGS, getTierBadgeColor, getTierDisplayName, getModelRequiredTier, canAccessModel } from "@/lib/openrouter/tiers"
import { 
  useOpenRouterCategories, 
  useCategoryRankings, 
  CATEGORY_COLOR_MAP,
  type CategoryWithIcon,
} from "@/hooks/use-openrouter-categories"

// Card data matching home page template card style exactly
const orchestrationCards = [
  {
    id: "elite",
    title: "Elite Mode",
    description: "Industry-leading orchestration strategies",
    icon: Crown,
    color: "from-yellow-500 to-amber-600",
    isPremium: true,
  },
  {
    id: "models",
    title: "Models",
    description: "Select AI models for multi-agent orchestration",
    icon: Cpu,
    color: "from-orange-500 to-amber-500",
  },
  {
    id: "reasoning",
    title: "Reasoning",
    description: "Advanced reasoning methods and techniques",
    icon: Brain,
    color: "from-purple-500 to-indigo-500",
  },
  {
    id: "tuning",
    title: "Tuning",
    description: "Fine-tune response behavior and validation",
    icon: Sliders,
    color: "from-emerald-500 to-teal-500",
  },
  {
    id: "features",
    title: "Features",
    description: "RAG, MCP, memory and more capabilities",
    icon: Wrench,
    color: "from-blue-500 to-cyan-500",
  },
  {
    id: "tools",
    title: "Tools",
    description: "External integrations and tool access",
    icon: Hammer,
    color: "from-rose-500 to-pink-500",
  },
  {
    id: "quality",
    title: "Quality",
    description: "Verification, challenge loops and fact-checking",
    icon: Shield,
    color: "from-green-500 to-emerald-600",
  },
  {
    id: "speed",
    title: "Speed",
    description: "Response speed and processing depth",
    icon: Zap,
    color: "from-cyan-500 to-sky-500",
  },
]

// Elite Mode strategies
const eliteStrategies = [
  { id: "fast", label: "Fast", description: "Quick single-model responses", confidence: "70%" },
  { id: "standard", label: "Standard", description: "Multi-model with verification", confidence: "80%" },
  { id: "thorough", label: "Thorough", description: "Full pipeline with challenge loop", confidence: "90%" },
  { id: "exhaustive", label: "Exhaustive", description: "All techniques including debate", confidence: "95%" },
]

// Quality assurance options
const qualityOptions = [
  { id: "verification", label: "Fact Verification", description: "Verify all factual claims" },
  { id: "challenge", label: "Challenge Loop", description: "Adversarial stress-testing of answers" },
  { id: "consensus", label: "Multi-Model Consensus", description: "Agreement between multiple models" },
  { id: "reflection", label: "Self-Reflection", description: "Models critique and improve their output" },
  { id: "tools", label: "Tool Integration", description: "Use search, calculator, code execution" },
]

// Features list
const featuresList = [
  { id: "vector-rag", label: "Vector DB + RAG", description: "Retrieval augmented generation with vector database" },
  { id: "mcp-server", label: "MCP Server + Tools", description: "Model context protocol for tool orchestration" },
  { id: "personal-database", label: "Personal Database", description: "Your private knowledge base" },
  { id: "modular-answer-feed", label: "Modular Answer Feed", description: "Internal LLM routing and composition" },
  { id: "memory-augmentation", label: "Memory Augmentation", description: "Long-term conversation memory" },
  { id: "code-interpreter", label: "Code Interpreter", description: "Execute code in a sandboxed environment" },
]

// Tools list
const toolsList = [
  { id: "web-search", label: "Web Search", description: "Search the internet for real-time information" },
  { id: "code-execution", label: "Code Execution", description: "Run Python, JavaScript, and more" },
  { id: "file-analysis", label: "File Analysis", description: "Parse and analyze documents" },
  { id: "image-generation", label: "Image Generation", description: "Create images from text" },
  { id: "data-visualization", label: "Data Visualization", description: "Generate charts and graphs" },
  { id: "api-integration", label: "API Integration", description: "Connect to external APIs" },
]

// Tuning options
const tuningOptions = [
  {
    key: "promptOptimization",
    label: "Prompt Optimization",
    description: "Automatically enhance prompts",
    icon: Sparkles,
  },
  {
    key: "outputValidation",
    label: "Output Validation",
    description: "Verify and fact-check responses",
    icon: Check,
  },
  { key: "answerStructure", label: "Answer Structure", description: "Format with clear sections", icon: Layers },
  { key: "sharedMemory", label: "Shared Memory", description: "Access previous conversations", icon: Hammer },
  {
    key: "learnFromChat",
    label: "Learn from Chat",
    description: "Improve from this conversation",
    icon: Wrench,
  },
]

// Standard settings
const standardSettings = [
  {
    id: "temperature",
    label: "Temperature",
    description: "Controls randomness (0-2)",
    min: 0,
    max: 2,
    step: 0.1,
    default: 0.7,
  },
  {
    id: "maxTokens",
    label: "Max Tokens",
    description: "Maximum response length",
    min: 100,
    max: 4000,
    step: 100,
    default: 2000,
  },
  { id: "topP", label: "Top P", description: "Nucleus sampling threshold", min: 0, max: 1, step: 0.05, default: 0.9 },
  {
    id: "frequencyPenalty",
    label: "Frequency Penalty",
    description: "Reduce repetition",
    min: 0,
    max: 2,
    step: 0.1,
    default: 0,
  },
  {
    id: "presencePenalty",
    label: "Presence Penalty",
    description: "Encourage new topics",
    min: 0,
    max: 2,
    step: 0.1,
    default: 0,
  },
]

const speedOptions = [
  { id: "fast", label: "Fast", description: "Quick responses with minimal processing" },
  { id: "standard", label: "Standard", description: "Balanced speed and quality" },
  { id: "deep", label: "Deep", description: "Thorough analysis with extended processing" },
]

type DrawerId = "models" | "reasoning" | "tuning" | "features" | "tools" | "standard" | "speed" | "elite" | "quality" | null

export default function OrchestrationPage() {
  const router = useRouter()
  const auth = useAuth()
  const [activeDrawer, setActiveDrawer] = useState<DrawerId>(null)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [settingsLoaded, setSettingsLoaded] = useState(false)

  // State for all settings
  const [selectedModels, setSelectedModels] = useState<string[]>(["automatic"])
  const [openRouterModels, setOpenRouterModels] = useState<SelectedModelConfig[]>([])
  const [selectedMethods, setSelectedMethods] = useState<string[]>([])
  const [selectedFeatures, setSelectedFeatures] = useState<string[]>([])
  const [selectedTools, setSelectedTools] = useState<string[]>([])
  const [tuningSettings, setTuningSettings] = useState({
    promptOptimization: true,
    outputValidation: true,
    answerStructure: false,
    sharedMemory: true,
    learnFromChat: false,
  })
  const [standardValues, setStandardValues] = useState({
    temperature: 0.7,
    maxTokens: 2000,
    topP: 0.9,
    frequencyPenalty: 0,
    presencePenalty: 0,
  })
  const [selectedSpeed, setSelectedSpeed] = useState<string>("standard")
  const [selectedEliteStrategy, setSelectedEliteStrategy] = useState<string>("standard")
  const [selectedQualityOptions, setSelectedQualityOptions] = useState<string[]>(["verification", "consensus"])
  
  // TODO: Get from auth context
  const userTier: UserTier = 'pro'
  const tierConfig = TIER_CONFIGS[userTier]
  
  // Category-based model selection state
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  
  // Use shared hooks for categories and rankings
  const { categories, loading: categoriesLoading } = useOpenRouterCategories({ group: 'usecase' })
  const { rankings: rankedEntries, loading: loadingRankings } = useCategoryRankings(activeCategory, { limit: 10 })
  
  // Category icons mapping
  const CATEGORY_ICONS: Record<string, React.ElementType> = {
    'programming': Code,
    'science': FlaskConical,
    'health': Heart,
    'legal': Scale,
    'marketing': Megaphone,
    'marketing/seo': Search,
    'technology': Cpu,
    'finance': Landmark,
    'academia': GraduationCap,
    'roleplay': Users,
    'creative-writing': MessageSquare,
    'translation': Languages,
    'data-analysis': BarChart3,
    'tool-use': ToolIcon,
    'vision': ImageIcon,
    'reasoning': FlaskConical,
  }
  
  const getCategoryIcon = (slug: string): React.ElementType => {
    return CATEGORY_ICONS[slug] || BarChart3
  }

  // Load settings from localStorage on mount
  useEffect(() => {
    const savedSettings = loadOrchestratorSettings()
    setSelectedModels(savedSettings.selectedModels || ["automatic"])
    setSelectedMethods(savedSettings.advancedReasoningMethods || [])
    setSelectedFeatures(savedSettings.advancedFeatures || [])
    setSelectedTools(savedSettings.advancedFeatures?.filter(f => 
      ["web-search", "code-execution", "file-analysis", "image-generation", "data-visualization", "api-integration"].includes(f)
    ) || [])
    setTuningSettings({
      promptOptimization: savedSettings.promptOptimization,
      outputValidation: savedSettings.outputValidation,
      answerStructure: savedSettings.answerStructure,
      sharedMemory: savedSettings.sharedMemory,
      learnFromChat: savedSettings.learnFromChat,
    })
    setSelectedSpeed(savedSettings.reasoningMode || "standard")
    setSelectedEliteStrategy(savedSettings.eliteStrategy || "standard")
    setSelectedQualityOptions(savedSettings.qualityOptions || ["verification", "consensus"])
    // Load standard LLM values
    if (savedSettings.standardValues) {
      setStandardValues(savedSettings.standardValues)
    }
    
    // Load OpenRouter models from localStorage
    try {
      const storedPrefs = localStorage.getItem(STORAGE_KEYS.USER_MODEL_PREFERENCES)
      if (storedPrefs) {
        const prefs = JSON.parse(storedPrefs)
        if (prefs.selectedModels) {
          setOpenRouterModels(prefs.selectedModels)
        }
      }
    } catch (e) {
      console.error('Failed to load OpenRouter preferences:', e)
    }
    
    setSettingsLoaded(true)
  }, [])

  // Save settings to localStorage when they change
  useEffect(() => {
    if (!settingsLoaded) return // Don't save during initial load
    
    saveOrchestratorSettings({
      selectedModels,
      advancedReasoningMethods: selectedMethods as any,
      advancedFeatures: [...selectedFeatures, ...selectedTools] as any,
      promptOptimization: tuningSettings.promptOptimization,
      outputValidation: tuningSettings.outputValidation,
      answerStructure: tuningSettings.answerStructure,
      sharedMemory: tuningSettings.sharedMemory,
      learnFromChat: tuningSettings.learnFromChat,
      reasoningMode: selectedSpeed as any,
      eliteStrategy: selectedEliteStrategy as any,
      qualityOptions: selectedQualityOptions as any,
      standardValues: standardValues,
    })
  }, [selectedModels, selectedMethods, selectedFeatures, selectedTools, tuningSettings, selectedSpeed, selectedEliteStrategy, selectedQualityOptions, standardValues, settingsLoaded])

  const toggleModel = (id: string) => {
    setSelectedModels((prev) => (prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]))
  }

  const toggleMethod = (id: string) => {
    setSelectedMethods((prev) => (prev.includes(id) ? prev.filter((m) => m !== id) : [...prev, id]))
  }

  const toggleFeature = (id: string) => {
    setSelectedFeatures((prev) => (prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id]))
  }

  const toggleTool = (id: string) => {
    setSelectedTools((prev) => (prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]))
  }

  const toggleQualityOption = (id: string) => {
    setSelectedQualityOptions((prev) => (prev.includes(id) ? prev.filter((q) => q !== id) : [...prev, id]))
  }

  const getCount = (id: string) => {
    switch (id) {
      case "models":
        // Count both built-in models and OpenRouter models
        const enabledOpenRouterCount = openRouterModels.filter(m => m.enabled).length
        return selectedModels.length + enabledOpenRouterCount
      case "reasoning":
        return selectedMethods.length
      case "features":
        return selectedFeatures.length
      case "tools":
        return selectedTools.length
      case "tuning":
        return Object.values(tuningSettings).filter(Boolean).length
      case "speed":
        return 1
      case "elite":
        return 1 // Always show the selected strategy
      case "quality":
        return selectedQualityOptions.length
      default:
        return 0
    }
  }

  return (
    <div className="flex h-screen overflow-hidden relative">
      {/* Sign In Button - Top Right (outside of main content flow) */}
      <div className="hidden md:block fixed top-3 right-3 z-50">
        <UserAccountMenu />
      </div>

      {/* Glassmorphism Sidebar */}
      <div className="llmhive-glass-sidebar h-full">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        conversations={[]}
        currentConversationId={null}
        onSelectConversation={() => router.push(ROUTES.HOME)}
        onNewChat={() => router.push(ROUTES.HOME)}
        onDeleteConversation={() => {}}
        onTogglePin={() => {}}
        onRenameConversation={() => {}}
        onMoveToProject={() => {}}
        projects={[]}
        onGoHome={() => router.push(ROUTES.HOME)}
      />
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {/* Main Content in scrollable container */}
        <div className="flex-1 h-full overflow-auto">
          <div className="min-h-full flex flex-col items-center justify-start px-4 pt-4 pb-20">
            {/* Hero Section with 3D Logo */}
            <div className="text-center mb-6 llmhive-fade-in">
              <div className="relative w-52 h-52 md:w-[340px] md:h-[340px] lg:w-[378px] lg:h-[378px] mx-auto -mb-14 md:-mb-24 llmhive-float">
                <Image src="/logo.png" alt="LLMHive" fill className="object-contain drop-shadow-2xl" priority />
              </div>
              <LogoText height={64} className="md:hidden mb-2 mx-auto" />
              <LogoText height={92} className="hidden md:block lg:hidden mb-2 mx-auto" />
              <LogoText height={110} className="hidden lg:block mb-2 mx-auto" />
              <h2 className="text-xl md:text-2xl lg:text-3xl llmhive-subtitle mb-2">
                Orchestration
              </h2>
              <p className="text-muted-foreground text-sm md:text-base max-w-md mx-auto">
                Configure your multi-agent AI system with precision
              </p>
            </div>

            {/* Orchestration Cards - Glassmorphism Style */}
            <div className="w-full max-w-5xl llmhive-fade-in" style={{ animationDelay: '0.1s' }}>
              <p className="text-sm text-muted-foreground text-center mb-3">Select a category to configure</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-8 gap-3">
                {orchestrationCards.map((card, index) => {
                  const Icon = card.icon
                  const count = getCount(card.id)
                  const badgeClasses: Record<string, string> = {
                    "elite": "icon-badge-yellow",
                    "models": "icon-badge-orange",
                    "reasoning": "icon-badge-purple",
                    "tuning": "icon-badge-emerald",
                    "features": "icon-badge-blue",
                    "tools": "icon-badge-rose",
                    "quality": "icon-badge-teal",
                    "speed": "icon-badge-teal",
                  }
                  return (
                    <button
                      key={card.id}
                      onClick={() => setActiveDrawer(card.id as DrawerId)}
                      className="settings-card group llmhive-fade-in"
                      style={{ animationDelay: `${0.15 + index * 0.03}s` }}
                    >
                      {/* Count Badge */}
                      {count > 0 && (
                        <Badge className="absolute top-2 right-2 bronze-gradient text-black text-xs px-1.5 py-0.5 font-semibold">
                          {count}
                        </Badge>
                      )}
                      {/* Icon Badge */}
                      <div className={`icon-badge ${badgeClasses[card.id] || 'icon-badge-blue'}`}>
                        <Icon className="h-5 w-5 md:h-6 md:w-6 text-white" />
                      </div>
                      {/* Card Text */}
                      <div className="space-y-0.5 text-center">
                        <h3 className="font-semibold text-sm md:text-base text-foreground group-hover:text-[var(--gold)] transition-colors">
                          {card.title}
                        </h3>
                        <p className="text-xs text-muted-foreground leading-tight line-clamp-2 hidden sm:block">{card.description}</p>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Models Drawer */}
      <Sheet open={activeDrawer === "models"} onOpenChange={(open) => !open && setActiveDrawer(null)}>
        <SheetContent
          side="right"
          className="w-[300px] sm:w-[340px] bg-background/95 backdrop-blur-xl border-l border-border/50 p-0"
        >
          <div className="p-5 border-b border-border/50">
            <SheetHeader className="space-y-1">
              <SheetTitle className="text-base font-medium flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center">
                  <Cpu className="h-4 w-4 text-blue-400" />
                </div>
                Models
                <span className="ml-auto text-xs font-normal text-[var(--bronze)] bg-[var(--bronze)]/10 px-2 py-0.5 rounded-full">
                  {selectedModels.length + openRouterModels.filter(m => m.enabled).length} selected
                </span>
              </SheetTitle>
              <p className="text-xs text-muted-foreground">Select AI models for orchestration</p>
            </SheetHeader>
          </div>
          <ScrollArea className="h-[calc(100vh-100px)]">
            <div className="p-4 space-y-4">
              {activeCategory ? (
                // Show top 10 models for selected category
                <>
                  <div className="flex items-center gap-2 pb-2 border-b border-border/50">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="h-7 w-7 p-0"
                      onClick={() => setActiveCategory(null)}
                    >
                      <ArrowLeft className="h-4 w-4" />
                    </Button>
                    <span className="font-medium text-sm">
                      Top 10 - {categories.find(c => c.slug === activeCategory)?.displayName || activeCategory}
                    </span>
                  </div>
                  {loadingRankings ? (
                    <div className="p-4 text-center text-muted-foreground text-sm">
                      <Loader2 className="h-4 w-4 animate-spin mx-auto mb-1" />
                      Loading...
                    </div>
                  ) : rankedEntries.length > 0 ? (
                    <div className="space-y-1.5">
                      {rankedEntries.map((entry) => {
                        const modelId = entry.model_id || ''
                        const isSelected = selectedModels.includes(modelId)
                        const hasAccess = canAccessModel(userTier, modelId)
                        const requiredTier = getModelRequiredTier(modelId)
                        
                        return (
                          <div
                            key={modelId}
                            onClick={() => hasAccess && toggleModel(modelId)}
                            className={`group p-2.5 rounded-lg transition-all duration-200 ${
                              !hasAccess ? "opacity-50 cursor-not-allowed" :
                              isSelected ? "bg-[var(--bronze)]/10 ring-1 ring-[var(--bronze)]/30 cursor-pointer" : "hover:bg-muted/50 cursor-pointer"
                            }`}
                          >
                            <div className="flex items-center gap-2.5">
                              <div className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 ${
                                entry.rank === 1 ? "bg-yellow-400 text-yellow-900" :  // Gold
                                entry.rank === 2 ? "bg-slate-300 text-slate-700" :    // Silver
                                entry.rank === 3 ? "bg-amber-600 text-amber-100" :    // Bronze
                                "bg-muted text-muted-foreground"
                              }`}>
                                {entry.rank}
                              </div>
                              {/* Provider Logo */}
                              {getModelLogo(modelId) && (
                                <div className="w-4 h-4 relative shrink-0">
                                  <Image
                                    src={getModelLogo(modelId)}
                                    alt=""
                                    fill
                                    className="object-contain"
                                    unoptimized
                                  />
                                </div>
                              )}
                              <div className="flex-1 min-w-0">
                                <p className={`text-sm font-medium truncate ${isSelected ? "text-[var(--bronze)]" : ""}`}>
                                  {entry.model_name}
                                </p>
                                <div className="flex items-center gap-1.5">
                                  <span className="text-[10px] text-muted-foreground">
                                    {entry.author || entry.model_id?.split('/')[0]}
                                  </span>
                                  {!hasAccess && (
                                    <Badge variant="outline" className={`text-[8px] px-1 py-0 ${getTierBadgeColor(requiredTier)}`}>
                                      {getTierDisplayName(requiredTier)}
                                    </Badge>
                                  )}
                                </div>
                              </div>
                              {isSelected && <Check className="h-4 w-4 text-[var(--bronze)]" />}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  ) : (
                    <div className="p-4 text-center text-muted-foreground text-sm">No models found</div>
                  )}
                </>
              ) : (
                // Show categories list
                <>
                  {/* Automatic Option - Always at top */}
                  <div
                    onClick={() => setSelectedModels(["automatic"])}
                    className={`group p-3 rounded-lg cursor-pointer transition-all duration-200 ${
                      selectedModels.includes("automatic") ? "bg-[var(--bronze)]/10 ring-1 ring-[var(--bronze)]/30" : "hover:bg-muted/50"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[var(--bronze)] to-amber-600 flex items-center justify-center">
                        <Sparkles className="h-4 w-4 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm font-medium ${selectedModels.includes("automatic") ? "text-[var(--bronze)]" : ""}`}>
                          Automatic
                        </p>
                        <p className="text-[10px] text-muted-foreground">Best model selected per task</p>
                      </div>
                      {selectedModels.includes("automatic") && <Check className="h-4 w-4 text-[var(--bronze)]" />}
                    </div>
                  </div>
                  
                  {/* Divider */}
                  <div className="relative py-2">
                    <div className="absolute inset-0 flex items-center">
                      <span className="w-full border-t border-border" />
                    </div>
                    <div className="relative flex justify-center text-[10px] uppercase">
                      <span className="bg-background px-2 text-muted-foreground">Browse by Category</span>
                    </div>
                  </div>
                  
                  {/* Categories */}
                  {categoriesLoading ? (
                    <div className="p-4 text-center text-muted-foreground text-sm">
                      <Loader2 className="h-4 w-4 animate-spin mx-auto mb-1" />
                      Loading categories...
                    </div>
                  ) : (
                    <div className="space-y-1.5">
                      {categories.map((cat) => {
                        const Icon = getCategoryIcon(cat.slug)
                        return (
                          <div
                            key={cat.slug}
                            onClick={() => setActiveCategory(cat.slug)}
                            className="group p-2.5 rounded-lg cursor-pointer transition-all duration-200 hover:bg-muted/50"
                          >
                            <div className="flex items-center gap-2.5">
                              <Icon className={`h-4 w-4 ${CATEGORY_COLOR_MAP[cat.slug] || "text-muted-foreground"}`} />
                              <span className="flex-1 text-sm">{cat.displayName}</span>
                              <ChevronRight className="h-4 w-4 text-muted-foreground" />
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                  
                  {/* My Team Section */}
                  {openRouterModels.length > 0 && (
                    <>
                      <div className="relative py-2">
                        <div className="absolute inset-0 flex items-center">
                          <span className="w-full border-t border-border" />
                        </div>
                        <div className="relative flex justify-center text-[10px] uppercase">
                          <span className="bg-background px-2 text-muted-foreground">Your Team</span>
                        </div>
                      </div>
                      <div className="space-y-1.5">
                        {openRouterModels.map((config) => {
                          const modelName = config.modelId.split('/').pop() || config.modelId
                          const isSelected = selectedModels.includes(config.modelId)
                          return (
                            <div
                              key={config.modelId}
                              onClick={() => toggleModel(config.modelId)}
                              className={`group p-2.5 rounded-lg cursor-pointer transition-all duration-200 ${
                                isSelected ? "bg-[var(--bronze)]/10 ring-1 ring-[var(--bronze)]/30" : "hover:bg-muted/50"
                              }`}
                            >
                              <div className="flex items-center gap-2.5">
                                <Crown className="h-4 w-4 text-[var(--bronze)]" />
                                <span className="flex-1 text-sm truncate">{modelName}</span>
                                {isSelected && <Check className="h-4 w-4 text-[var(--bronze)]" />}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </>
                  )}
                  
                  {/* Manage Team Link */}
                  <Link href={ROUTES.MODELS}>
                    <Button variant="outline" size="sm" className="w-full gap-2 mt-2">
                      <Plus className="h-3.5 w-3.5" />
                      {openRouterModels.length > 0 ? "Manage Team" : "Build Your AI Team"}
                      <ArrowRight className="h-3.5 w-3.5 ml-auto" />
                    </Button>
                  </Link>
                </>
              )}
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>

      {/* Reasoning Drawer */}
      <Sheet open={activeDrawer === "reasoning"} onOpenChange={(open) => !open && setActiveDrawer(null)}>
        <SheetContent
          side="right"
          className="w-[260px] sm:w-[280px] bg-background/95 backdrop-blur-xl border-l border-border/50 p-0"
        >
          <div className="p-5 border-b border-border/50">
            <SheetHeader className="space-y-1">
              <SheetTitle className="text-base font-medium flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center">
                  <Brain className="h-4 w-4 text-purple-400" />
                </div>
                Reasoning
                <span className="ml-auto text-xs font-normal text-[var(--bronze)] bg-[var(--bronze)]/10 px-2 py-0.5 rounded-full">
                  {selectedMethods.length} selected
                </span>
              </SheetTitle>
              <p className="text-xs text-muted-foreground">Advanced reasoning methods</p>
            </SheetHeader>
          </div>
          <ScrollArea className="h-[calc(100vh-100px)]">
            <div className="p-4">
              {REASONING_CATEGORIES.map((category) => {
                const categoryMethods = REASONING_METHODS.filter((m) => m.category === category)
                return (
                  <div key={category} className="mb-5">
                    <h3 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-2 px-1">
                      {category}
                    </h3>
                    <div className="space-y-1.5">
                      {categoryMethods.map((method) => {
                        const isSelected = selectedMethods.includes(method.id)
                        return (
                          <div
                            key={method.id}
                            onClick={() => toggleMethod(method.id)}
                            className={`group p-2.5 rounded-lg cursor-pointer transition-all duration-200 ${
                              isSelected ? "bg-[var(--bronze)]/10 ring-1 ring-[var(--bronze)]/30" : "hover:bg-muted/50"
                            }`}
                          >
                            <div className="flex items-center gap-2.5">
                              <div
                                className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all flex-shrink-0 ${
                                  isSelected
                                    ? "border-[var(--bronze)] bg-[var(--bronze)]"
                                    : "border-muted-foreground/30 group-hover:border-muted-foreground/50"
                                }`}
                              >
                                {isSelected && <Check className="h-2.5 w-2.5 text-background" />}
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-1.5">
                                  <p className="text-sm font-medium truncate">{method.name}</p>
                                  <span className="text-[9px] text-muted-foreground bg-muted/50 px-1 rounded">
                                    {method.year}
                                  </span>
                                </div>
                              </div>
                              <a
                                href={method.referenceUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="opacity-0 group-hover:opacity-100 transition-opacity"
                                onClick={(e) => e.stopPropagation()}
                              >
                                <ExternalLink className="h-3 w-3 text-muted-foreground hover:text-[var(--bronze)]" />
                              </a>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )
              })}
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>

      {/* Tuning Drawer */}
      <Sheet open={activeDrawer === "tuning"} onOpenChange={(open) => !open && setActiveDrawer(null)}>
        <SheetContent
          side="right"
          className="w-[260px] sm:w-[280px] bg-background/95 backdrop-blur-xl border-l border-border/50 p-0"
        >
          <div className="p-5 border-b border-border/50">
            <SheetHeader className="space-y-1">
              <SheetTitle className="text-base font-medium flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500/20 to-orange-500/20 flex items-center justify-center">
                  <Sliders className="h-4 w-4 text-amber-400" />
                </div>
                Tuning
                <span className="ml-auto text-xs font-normal text-[var(--bronze)] bg-[var(--bronze)]/10 px-2 py-0.5 rounded-full">
                  {Object.values(tuningSettings).filter(Boolean).length} enabled
                </span>
              </SheetTitle>
              <p className="text-xs text-muted-foreground">Fine-tune response behavior</p>
            </SheetHeader>
          </div>
          <ScrollArea className="h-[calc(100vh-100px)]">
            <div className="p-4 space-y-1.5">
              {tuningOptions.map((option) => {
                const isEnabled = tuningSettings[option.key as keyof typeof tuningSettings]
                return (
                  <div
                    key={option.key}
                    onClick={() =>
                      setTuningSettings((prev) => ({ ...prev, [option.key]: !prev[option.key as keyof typeof prev] }))
                    }
                    className={`group p-2.5 rounded-lg cursor-pointer transition-all duration-200 ${
                      isEnabled ? "bg-[var(--bronze)]/10 ring-1 ring-[var(--bronze)]/30" : "hover:bg-muted/50"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <div
                        className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all flex-shrink-0 ${
                          isEnabled
                            ? "border-[var(--bronze)] bg-[var(--bronze)]"
                            : "border-muted-foreground/30 group-hover:border-muted-foreground/50"
                        }`}
                      >
                        {isEnabled && <Check className="h-2.5 w-2.5 text-background" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm font-medium ${isEnabled ? "text-[var(--bronze)]" : ""}`}>
                          {option.label}
                        </p>
                        <p className="text-[10px] text-muted-foreground leading-tight">{option.description}</p>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>

      {/* Features Drawer */}
      <Sheet open={activeDrawer === "features"} onOpenChange={(open) => !open && setActiveDrawer(null)}>
        <SheetContent
          side="right"
          className="w-[260px] sm:w-[280px] bg-background/95 backdrop-blur-xl border-l border-border/50 p-0"
        >
          <div className="p-5 border-b border-border/50">
            <SheetHeader className="space-y-1">
              <SheetTitle className="text-base font-medium flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-green-500/20 to-emerald-500/20 flex items-center justify-center">
                  <Wrench className="h-4 w-4 text-green-400" />
                </div>
                Features
                <span className="ml-auto text-xs font-normal text-[var(--bronze)] bg-[var(--bronze)]/10 px-2 py-0.5 rounded-full">
                  {selectedFeatures.length} enabled
                </span>
              </SheetTitle>
              <p className="text-xs text-muted-foreground">Advanced capabilities</p>
            </SheetHeader>
          </div>
          <ScrollArea className="h-[calc(100vh-100px)]">
            <div className="p-4 space-y-1.5">
              {featuresList.map((feature) => {
                const isSelected = selectedFeatures.includes(feature.id)
                return (
                  <div
                    key={feature.id}
                    onClick={() => toggleFeature(feature.id)}
                    className={`group p-2.5 rounded-lg cursor-pointer transition-all duration-200 ${
                      isSelected ? "bg-[var(--bronze)]/10 ring-1 ring-[var(--bronze)]/30" : "hover:bg-muted/50"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <div
                        className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all flex-shrink-0 ${
                          isSelected
                            ? "border-[var(--bronze)] bg-[var(--bronze)]"
                            : "border-muted-foreground/30 group-hover:border-muted-foreground/50"
                        }`}
                      >
                        {isSelected && <Check className="h-2.5 w-2.5 text-background" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm font-medium ${isSelected ? "text-[var(--bronze)]" : ""}`}>
                          {feature.label}
                        </p>
                        <p className="text-[10px] text-muted-foreground leading-tight">{feature.description}</p>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>

      {/* Tools Drawer */}
      <Sheet open={activeDrawer === "tools"} onOpenChange={(open) => !open && setActiveDrawer(null)}>
        <SheetContent
          side="right"
          className="w-[260px] sm:w-[280px] bg-background/95 backdrop-blur-xl border-l border-border/50 p-0"
        >
          <div className="p-5 border-b border-border/50">
            <SheetHeader className="space-y-1">
              <SheetTitle className="text-base font-medium flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-rose-500/20 to-red-500/20 flex items-center justify-center">
                  <Hammer className="h-4 w-4 text-rose-400" />
                </div>
                Tools
                <span className="ml-auto text-xs font-normal text-[var(--bronze)] bg-[var(--bronze)]/10 px-2 py-0.5 rounded-full">
                  {selectedTools.length} enabled
                </span>
              </SheetTitle>
              <p className="text-xs text-muted-foreground">External integrations</p>
            </SheetHeader>
          </div>
          <ScrollArea className="h-[calc(100vh-100px)]">
            <div className="p-4 space-y-1.5">
              {toolsList.map((tool) => {
                const isSelected = selectedTools.includes(tool.id)
                return (
                  <div
                    key={tool.id}
                    onClick={() => toggleTool(tool.id)}
                    className={`group p-2.5 rounded-lg cursor-pointer transition-all duration-200 ${
                      isSelected ? "bg-[var(--bronze)]/10 ring-1 ring-[var(--bronze)]/30" : "hover:bg-muted/50"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <div
                        className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all flex-shrink-0 ${
                          isSelected
                            ? "border-[var(--bronze)] bg-[var(--bronze)]"
                            : "border-muted-foreground/30 group-hover:border-muted-foreground/50"
                        }`}
                      >
                        {isSelected && <Check className="h-2.5 w-2.5 text-background" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm font-medium ${isSelected ? "text-[var(--bronze)]" : ""}`}>
                          {tool.label}
                        </p>
                        <p className="text-[10px] text-muted-foreground leading-tight">{tool.description}</p>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>

      {/* Standard Drawer */}
      <Sheet open={activeDrawer === "standard"} onOpenChange={(open) => !open && setActiveDrawer(null)}>
        <SheetContent
          side="right"
          className="w-[260px] sm:w-[280px] bg-background/95 backdrop-blur-xl border-l border-border/50 p-0"
        >
          <div className="p-4 border-b border-border/50">
            <SheetHeader className="space-y-1">
              <SheetTitle className="text-sm font-medium flex items-center gap-2">
                <div className="w-6 h-6 rounded-md bg-gradient-to-br from-indigo-500/20 to-violet-500/20 flex items-center justify-center">
                  <Layers className="h-3 w-3 text-indigo-400" />
                </div>
                Standard
              </SheetTitle>
              <p className="text-[10px] text-muted-foreground">Temperature, tokens & sampling</p>
            </SheetHeader>
          </div>
          <div className="p-4 space-y-4">
            {standardSettings.map((setting) => (
              <div key={setting.id} className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label className="text-xs font-medium">{setting.label}</Label>
                  <span className="text-[10px] font-mono text-[var(--bronze)] bg-[var(--bronze)]/10 px-1.5 py-0.5 rounded">
                    {standardValues[setting.id as keyof typeof standardValues]}
                  </span>
                </div>
                <Slider
                  value={[standardValues[setting.id as keyof typeof standardValues]]}
                  onValueChange={([value]) => setStandardValues((prev) => ({ ...prev, [setting.id]: value }))}
                  min={setting.min}
                  max={setting.max}
                  step={setting.step}
                  className="[&_[role=slider]]:bg-[var(--bronze)] [&_[role=slider]]:border-[var(--bronze)] [&_[role=slider]]:w-3 [&_[role=slider]]:h-3 [&_.bg-primary]:bg-[var(--bronze)]"
                />
                <p className="text-[9px] text-muted-foreground">{setting.description}</p>
              </div>
            ))}
          </div>
        </SheetContent>
      </Sheet>

      <Sheet open={activeDrawer === "speed"} onOpenChange={(open) => !open && setActiveDrawer(null)}>
        <SheetContent
          side="right"
          className="w-[260px] sm:w-[280px] bg-background/95 backdrop-blur-xl border-l border-border/50 p-0"
        >
          <div className="p-4 border-b border-border/50">
            <SheetHeader className="space-y-1">
              <SheetTitle className="text-sm font-medium flex items-center gap-2">
                <div className="w-6 h-6 rounded-md bg-gradient-to-br from-cyan-500/20 to-sky-500/20 flex items-center justify-center">
                  <Zap className="h-3 w-3 text-cyan-400" />
                </div>
                Speed
              </SheetTitle>
              <p className="text-[10px] text-muted-foreground">Response speed & processing depth</p>
            </SheetHeader>
          </div>
          <ScrollArea className="h-[calc(100vh-120px)]">
            <div className="p-3 space-y-1.5">
              {speedOptions.map((option) => {
                const isSelected = selectedSpeed === option.id
                return (
                  <button
                    key={option.id}
                    onClick={() => setSelectedSpeed(option.id)}
                    className={`w-full flex items-center gap-2.5 p-2.5 rounded-lg transition-all duration-200 ${
                      isSelected ? "bg-[var(--bronze)]/10 ring-1 ring-[var(--bronze)]/30" : "hover:bg-muted/50"
                    }`}
                  >
                    <div
                      className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all ${
                        isSelected ? "bg-[var(--bronze)] border-[var(--bronze)]" : "border-muted-foreground/30"
                      }`}
                    >
                      {isSelected && <Check className="h-2.5 w-2.5 text-black" />}
                    </div>
                    <div className="flex-1 text-left">
                      <p className={`text-xs font-medium ${isSelected ? "text-[var(--bronze)]" : "text-foreground"}`}>
                        {option.label}
                      </p>
                      <p className="text-[10px] text-muted-foreground">{option.description}</p>
                    </div>
                  </button>
                )
              })}
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>

      {/* Elite Mode Drawer */}
      <Sheet open={activeDrawer === "elite"} onOpenChange={(open) => !open && setActiveDrawer(null)}>
        <SheetContent
          side="right"
          className="w-[260px] sm:w-[280px] bg-background/95 backdrop-blur-xl border-l border-border/50 p-0"
        >
          <div className="p-5 border-b border-border/50">
            <SheetHeader className="space-y-1">
              <SheetTitle className="text-base font-medium flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-yellow-500/20 to-amber-500/20 flex items-center justify-center">
                  <Crown className="h-4 w-4 text-yellow-400" />
                </div>
                Elite Mode
                <Badge className="ml-auto bg-gradient-to-r from-yellow-500 to-amber-600 text-white text-[10px]">
                  PRO
                </Badge>
              </SheetTitle>
              <p className="text-xs text-muted-foreground">Industry-leading orchestration strategies</p>
            </SheetHeader>
          </div>
          <ScrollArea className="h-[calc(100vh-120px)]">
            <div className="p-4 space-y-3">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">
                Orchestration Strategy
              </p>
              {eliteStrategies.map((strategy) => {
                const isSelected = selectedEliteStrategy === strategy.id
                return (
                  <button
                    key={strategy.id}
                    onClick={() => setSelectedEliteStrategy(strategy.id)}
                    className={`w-full p-3 rounded-lg transition-all duration-200 text-left ${
                      isSelected ? "bg-[var(--bronze)]/10 ring-1 ring-[var(--bronze)]/30" : "hover:bg-muted/50 border border-border"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <div
                          className={`w-4 h-4 rounded-full border-2 flex items-center justify-center transition-all ${
                            isSelected ? "bg-[var(--bronze)] border-[var(--bronze)]" : "border-muted-foreground/30"
                          }`}
                        >
                          {isSelected && <Check className="h-2.5 w-2.5 text-black" />}
                        </div>
                        <span className={`text-sm font-medium ${isSelected ? "text-[var(--bronze)]" : ""}`}>
                          {strategy.label}
                        </span>
                      </div>
                      <Badge variant="secondary" className="text-[9px] bg-green-500/10 text-green-400">
                        {strategy.confidence}
                      </Badge>
                    </div>
                    <p className="text-[10px] text-muted-foreground ml-6">{strategy.description}</p>
                  </button>
                )
              })}
              
              <div className="pt-4 border-t border-border/50 mt-4">
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-3">
                  How It Works
                </p>
                <div className="space-y-2 text-[10px] text-muted-foreground">
                  <p>• <strong>Fast:</strong> Single best model, quick responses</p>
                  <p>• <strong>Standard:</strong> Multi-model with quality fusion</p>
                  <p>• <strong>Thorough:</strong> Challenge loop stress-tests answers</p>
                  <p>• <strong>Exhaustive:</strong> Expert panel + debate + verification</p>
                </div>
              </div>
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>

      {/* Quality Assurance Drawer */}
      <Sheet open={activeDrawer === "quality"} onOpenChange={(open) => !open && setActiveDrawer(null)}>
        <SheetContent
          side="right"
          className="w-[260px] sm:w-[280px] bg-background/95 backdrop-blur-xl border-l border-border/50 p-0"
        >
          <div className="p-5 border-b border-border/50">
            <SheetHeader className="space-y-1">
              <SheetTitle className="text-base font-medium flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-green-500/20 to-emerald-500/20 flex items-center justify-center">
                  <Shield className="h-4 w-4 text-green-400" />
                </div>
                Quality
                <span className="ml-auto text-xs font-normal text-[var(--bronze)] bg-[var(--bronze)]/10 px-2 py-0.5 rounded-full">
                  {selectedQualityOptions.length} enabled
                </span>
              </SheetTitle>
              <p className="text-xs text-muted-foreground">Verification and quality assurance</p>
            </SheetHeader>
          </div>
          <ScrollArea className="h-[calc(100vh-100px)]">
            <div className="p-4 space-y-1.5">
              {qualityOptions.map((option) => {
                const isSelected = selectedQualityOptions.includes(option.id)
                return (
                  <div
                    key={option.id}
                    onClick={() => toggleQualityOption(option.id)}
                    className={`group p-2.5 rounded-lg cursor-pointer transition-all duration-200 ${
                      isSelected ? "bg-[var(--bronze)]/10 ring-1 ring-[var(--bronze)]/30" : "hover:bg-muted/50"
                    }`}
                  >
                    <div className="flex items-center gap-2.5">
                      <div
                        className={`w-4 h-4 rounded border-2 flex items-center justify-center transition-all flex-shrink-0 ${
                          isSelected
                            ? "border-[var(--bronze)] bg-[var(--bronze)]"
                            : "border-muted-foreground/30 group-hover:border-muted-foreground/50"
                        }`}
                      >
                        {isSelected && <Check className="h-2.5 w-2.5 text-background" />}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm font-medium ${isSelected ? "text-[var(--bronze)]" : ""}`}>
                          {option.label}
                        </p>
                        <p className="text-[10px] text-muted-foreground leading-tight">{option.description}</p>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          </ScrollArea>
        </SheetContent>
      </Sheet>
    </div>
  )
}
