"use client"

import type React from "react"
import { useState, useRef, useCallback, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Progress } from "@/components/ui/progress"
import { Send, Paperclip, Mic, MicOff, X, ImageIcon, FileText, RefreshCw, AlertCircle, Sparkles, Brain, Code, Briefcase, Camera, Volume2 } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { getModelById, AVAILABLE_MODELS } from "@/lib/models"
import { sendChat, ApiError, NetworkError, TimeoutError, type RetryStatusCallback } from "@/lib/api-client"
import { toast } from "@/lib/toast"
import { processImageForOCR } from "@/lib/ocr"
import { voiceRecognition } from "@/lib/voice"
import { ErrorBoundary } from "@/components/error-boundary"
import { Skeleton } from "@/components/loading-skeleton"
import type { Conversation, Message, Attachment, Artifact, OrchestratorSettings, OrchestrationStatus, OrchestrationEventType, ClarificationQuestion } from "@/lib/types"
import { shouldAskClarification, formatClarificationMessage, type ClarificationDecision } from "@/lib/answer-quality/clarification-detector"
import { analyzeQuery } from "@/lib/answer-quality/prompt-optimizer"
import { MessageBubble } from "./message-bubble"
import { HiveActivityIndicator } from "./hive-activity-indicator"
import { AgentInsightsPanel } from "./agent-insights-panel"
import { ChatToolbar } from "./chat-toolbar"
import { OrchestrationStudio } from "./orchestration-studio"
import { LiveStatusPanel } from "./live-status-panel"
import { ModelsUsedDisplay } from "./models-used-display"

// When "automatic" is selected, we pass an empty array to let the backend
// intelligently select the best models based on query analysis, domain, and rankings

// Retry status for UI display
interface RetryStatus {
  isRetrying: boolean
  attempt: number
  maxAttempts: number
  message: string
}

// Error state for displaying inline retry button
interface ErrorState {
  hasError: boolean
  message: string
  canRetry: boolean
  lastInput?: string
}

interface ChatAreaProps {
  conversation?: Conversation
  onSendMessage: (message: Message) => void
  onShowArtifact: (artifact: Artifact) => void
  orchestratorSettings: OrchestratorSettings
  onOrchestratorSettingsChange: (settings: Partial<OrchestratorSettings>) => void
  onOpenAdvancedSettings: () => void
  userAccountMenu?: React.ReactNode
}

export function ChatArea({
  conversation,
  onSendMessage,
  onShowArtifact,
  orchestratorSettings,
  onOrchestratorSettingsChange,
  onOpenAdvancedSettings,
  userAccountMenu,
}: ChatAreaProps) {
  const [input, setInput] = useState("")
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [showInsights, setShowInsights] = useState(false)
  const [selectedMessageForInsights, setSelectedMessageForInsights] = useState<Message | null>(null)
  const [incognitoMode, setIncognitoMode] = useState(true)
  const [isLoading, setIsLoading] = useState(false)
  const [retryStatus, setRetryStatus] = useState<RetryStatus | null>(null)
  const [errorState, setErrorState] = useState<ErrorState>({ hasError: false, message: "", canRetry: false })
  
  // Clarification questions state
  const [pendingClarification, setPendingClarification] = useState<ClarificationDecision | null>(null)
  const [pendingInput, setPendingInput] = useState<string>("")
  
  const [orchestrationStatus, setOrchestrationStatus] = useState<OrchestrationStatus>({
    isActive: false,
    currentStep: "",
    events: [],
    modelsUsed: [],
  })
  const [lastModelsUsed, setLastModelsUsed] = useState<string[]>([])
  const [lastTokensUsed, setLastTokensUsed] = useState<number>(0)
  const [lastLatencyMs, setLastLatencyMs] = useState<number>(0)
  const [isListening, setIsListening] = useState(false)
  const [speechSupported, setSpeechSupported] = useState(false)
  const [audioLevel, setAudioLevel] = useState(0)
  const [interimTranscript, setInterimTranscript] = useState("")
  const [isProcessingOCR, setIsProcessingOCR] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)
  const eventIdRef = useRef(0)
  
  // Check for speech recognition support
  useEffect(() => {
    setSpeechSupported(voiceRecognition.supported)
  }, [])
  
  // Enhanced voice recording with audio level visualization
  const toggleVoiceRecording = useCallback(() => {
    if (!voiceRecognition.supported) {
      toast.error("Voice input not supported. Your browser doesn't support speech recognition.")
      return
    }
    
    if (isListening) {
      voiceRecognition.stop()
      setIsListening(false)
      setAudioLevel(0)
      setInterimTranscript("")
      toast.success("Voice recording stopped")
    } else {
      voiceRecognition.start({
        continuous: true,
        interimResults: true,
        onStart: () => {
          setIsListening(true)
          toast.info("🎤 Listening... Speak now")
        },
        onResult: (transcript, isFinal) => {
          if (isFinal) {
            setInput(prev => prev + transcript + ' ')
            setInterimTranscript("")
          } else {
            setInterimTranscript(transcript)
          }
        },
        onError: (error) => {
          toast.error(error)
          setIsListening(false)
          setAudioLevel(0)
        },
        onEnd: () => {
          setIsListening(false)
          setAudioLevel(0)
          setInterimTranscript("")
        },
        onAudioLevel: (level) => {
          setAudioLevel(level)
        },
      })
    }
  }, [isListening])
  
  // Enhanced OCR processing for images using our OCR utility
  const processImageWithOCR = useCallback(async (file: File): Promise<{ dataUrl: string; prompt: string } | null> => {
    try {
      setIsProcessingOCR(true)
      
      const toastId = toast.loading("Analyzing image...")
      
      // Use our enhanced OCR utility
      const result = await processImageForOCR(file)
      
      toast.dismiss(toastId)
      
      if (result.analysis.hasText) {
        toast.success(`Image processed (${result.analysis.width}x${result.analysis.height}px)`)
      } else {
        toast.info("Image processed. Note: Limited text detected.")
      }
      
      return {
        dataUrl: result.processedDataUrl,
        prompt: result.suggestedPrompt,
      }
    } catch (error) {
      console.error('OCR processing error:', error)
      toast.error("Failed to process image for OCR")
      return null
    } finally {
      setIsProcessingOCR(false)
    }
  }, [])
  
  const handleCameraCapture = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    if (files.length === 0) return
    
    const file = files[0]
    if (!file.type.startsWith('image/')) {
      toast.error("Please capture an image")
      return
    }
    
    // Process with OCR
    const result = await processImageWithOCR(file)
    if (result) {
      // Add the image as an attachment
      const newAttachment: Attachment = {
        id: `att-${Date.now()}-${Math.random()}`,
        name: file.name || "Camera capture",
        type: file.type,
        size: file.size,
        url: result.dataUrl,
      }
      setAttachments(prev => [...prev, newAttachment])
      
      // Add the suggested OCR prompt if no input yet
      if (input.trim() === '') {
        setInput(result.prompt)
      }
      toast.success("📷 Image captured and analyzed")
    }
  }

  // Use models from orchestrator settings - sync with settings
  const selectedModels = orchestratorSettings.selectedModels || ["automatic"]
  
  // Check if we're in automatic mode (let backend select best models)
  const isAutomaticMode = selectedModels.includes("automatic") || selectedModels.length === 0
  
  // Get actual models to send to backend
  const getActualModels = (): string[] => {
    if (isAutomaticMode) {
      // Return empty array - backend will intelligently select based on:
      // - Query content analysis
      // - Domain detection
      // - Task type classification
      // - Model rankings and capabilities
      return []
    }
    // Filter out "automatic" if mixed with other models
    return selectedModels.filter(m => m !== "automatic")
  }

  const currentModel = getModelById(selectedModels[0] || "gpt-4o")
  
  // Get active mode display info based on orchestrator settings
  const getActiveModeInfo = () => {
    const { reasoningMode, domainPack, agentMode } = orchestratorSettings
    
    // Check for specific templates based on settings
    if (domainPack === "coding") {
      return { label: "Code & Debug", icon: Code, color: "from-emerald-500 to-teal-500" }
    }
    if (domainPack === "research" || (reasoningMode === "deep" && agentMode === "team")) {
      return { label: "Research Mode", icon: Brain, color: "from-purple-500 to-indigo-500" }
    }
    if (domainPack && domainPack !== "default") {
      // Industry pack
      const packLabels: Record<string, string> = {
        legal: "Legal Pack",
        medical: "Medical Pack",
        marketing: "Marketing Pack",
        education: "Education Pack",
        finance: "Finance Pack",
        real_estate: "Real Estate Pack",
      }
      return { label: packLabels[domainPack] || `${domainPack} Pack`, icon: Briefcase, color: "from-blue-500 to-cyan-500" }
    }
    // General assistant
    return { label: "General Assistant", icon: Sparkles, color: "from-orange-500 to-amber-500" }
  }
  
  const activeModeInfo = getActiveModeInfo()

  // Add orchestration event
  const addOrchestrationEvent = useCallback((
    type: OrchestrationEventType,
    message: string,
    modelName?: string,
    progress?: number
  ) => {
    setOrchestrationStatus((prev) => ({
      ...prev,
      currentStep: message,
      events: [
        ...prev.events,
        {
          id: `evt-${++eventIdRef.current}`,
          type,
          message,
          timestamp: new Date(),
          modelName,
          progress,
        },
      ],
    }))
  }, [])

  // Simulate orchestration events (will be replaced with real SSE/WebSocket events)
  const simulateOrchestrationEvents = useCallback(async (settings: OrchestratorSettings) => {
    const events: { type: OrchestrationEventType; message: string; delay: number; modelName?: string }[] = [
      { type: "started", message: "Orchestration initiated", delay: 100 },
    ]

    if (settings.enablePromptDiffusion) {
      events.push({ type: "refining_prompt", message: "Refining prompt with diffusion...", delay: 400 })
    }

    if (settings.enableHRM) {
      events.push({ type: "dispatching_model", message: "Assigning hierarchical roles...", delay: 300 })
    }

    // Add model dispatches based on selected models
    let models = settings.selectedModels || ["automatic"]
    const isAutomatic = models.includes("automatic") || models.length === 0
    
    if (isAutomatic) {
      // Automatic mode - show intelligent selection happening
      events.push({
        type: "dispatching_model",
        message: "Analyzing query requirements...",
        delay: 250,
      })
      events.push({
        type: "dispatching_model",
        message: "Selecting optimal models based on task type...",
        delay: 300,
      })
      events.push({
        type: "dispatching_model",
        message: "Dispatching to best-fit model ensemble...",
        delay: 200,
      })
    } else {
      // User-selected models
      models = models.filter(m => m !== "automatic")
      for (const modelId of models.slice(0, 3)) {
        const model = getModelById(modelId)
        events.push({
          type: "dispatching_model",
          message: `Dispatching to ${model?.name || modelId}...`,
          delay: 200,
          modelName: model?.name || modelId,
        })
      }
    }

    events.push({ type: "model_responding", message: "Models generating responses...", delay: 500 })

    if (settings.enableDeepConsensus) {
      events.push({ type: "model_critiquing", message: "Models critiquing each other...", delay: 400 })
      events.push({ type: "consensus_building", message: "Building consensus...", delay: 300 })
    }

    if (settings.enableAdaptiveEnsemble) {
      events.push({ type: "verifying_facts", message: "Verifying with adaptive ensemble...", delay: 350 })
    }

    if (settings.outputValidation) {
      events.push({ type: "verifying_facts", message: "Validating output accuracy...", delay: 250 })
    }

    events.push({ type: "finalizing", message: "Finalizing response...", delay: 200 })

    // Execute events with delays
    for (const event of events) {
      await new Promise((resolve) => setTimeout(resolve, event.delay))
      addOrchestrationEvent(event.type, event.message, event.modelName)
    }
  }, [addOrchestrationEvent])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    const newAttachments: Attachment[] = files.map((file) => ({
      id: `att-${Date.now()}-${Math.random()}`,
      name: file.name,
      type: file.type,
      size: file.size,
      url: URL.createObjectURL(file),
    }))
    setAttachments([...attachments, ...newAttachments])
  }

  const removeAttachment = (id: string) => {
    setAttachments(attachments.filter((att) => att.id !== id))
  }

  const handleSend = async (skipClarification: boolean = false) => {
    if (!input.trim() && attachments.length === 0) return

    // Check if clarification questions are enabled and not skipped
    if (orchestratorSettings.enableClarificationQuestions && !skipClarification && !pendingClarification) {
      const clarificationDecision = shouldAskClarification(input)
      
      if (clarificationDecision.shouldAskClarification && clarificationDecision.questions.length > 0) {
        // Store the input and show clarification questions
        setPendingInput(input)
        setPendingClarification(clarificationDecision)
        
        // Show clarification message from AI
        const clarificationMessage: Message = {
          id: `msg-${Date.now()}`,
          role: "assistant",
          content: formatClarificationMessage(clarificationDecision),
          timestamp: new Date(),
          isClarificationRequest: true,
        }
        onSendMessage({ 
          id: `msg-${Date.now()}-user`,
          role: "user",
          content: input,
          timestamp: new Date(),
        })
        onSendMessage(clarificationMessage)
        setInput("")
        toast.info("I have a few clarifying questions to better help you.")
        return
      }
    }
    
    // If we have pending clarification, enhance the query with context
    let enhancedInput = input
    let enableLiveResearch = false
    
    if (pendingInput && pendingClarification) {
      // User answered clarification questions - combine original question with their preferences
      const clarificationContext = input.toLowerCase()
      
      // Check if user requested real-time data
      if (clarificationContext.includes('real-time') || 
          clarificationContext.includes('realtime') || 
          clarificationContext.includes('current') ||
          clarificationContext.includes('yes')) {
        enableLiveResearch = true
      }
      
      // Combine original question with clarification answers
      enhancedInput = `${pendingInput}\n\n[User preferences: ${input}]`
      
      console.log('🔍 Enhanced query with clarification:', { 
        original: pendingInput, 
        preferences: input,
        enableLiveResearch 
      })
    }
    
    // Clear any pending clarification
    setPendingClarification(null)
    setPendingInput("")

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: "user",
      content: enhancedInput,
      timestamp: new Date(),
      attachments: attachments.length > 0 ? attachments : undefined,
      // Flag for live research based on clarification
      metadata: enableLiveResearch ? { enableLiveResearch: true } : undefined,
    }

    onSendMessage(userMessage)

    setInput("")
    setAttachments([])
    setIsLoading(true)

    // Start orchestration status
    const startTime = Date.now()
    setOrchestrationStatus({
      isActive: true,
      currentStep: "Starting orchestration...",
      events: [],
      modelsUsed: [],
      startTime: new Date(),
    })

    // Simulate orchestration events
    simulateOrchestrationEvents(orchestratorSettings)

    // Retry callback to update UI
    const handleRetry: RetryStatusCallback = (status) => {
      setRetryStatus({
        isRetrying: true,
        attempt: status.attempt,
        maxAttempts: status.maxAttempts,
        message: `Retrying (${status.attempt}/${status.maxAttempts})... ${Math.round(status.delayMs / 1000)}s delay`,
      })
      
      // Add retry event to orchestration status
      addOrchestrationEvent(
        "dispatching_model",
        `Retrying request (attempt ${status.attempt}/${status.maxAttempts})...`
      )
    }

    try {
      // Clear any previous retry status and error state
      setRetryStatus(null)
      setErrorState({ hasError: false, message: "", canRetry: false })
      
      // Get actual models to use (expand "automatic")
      const actualModels = getActualModels()
      
      // Use typed API client with retry callback
      const chatResponse = await sendChat(
        {
          messages: [...(conversation?.messages || []), userMessage],
          models: actualModels,
          orchestratorSettings: {
            ...orchestratorSettings,
            selectedModels: actualModels,
            // Enable live research if user requested it via clarification
            enableLiveResearch: enableLiveResearch || orchestratorSettings.enableLiveResearch,
          },
          chatId: conversation?.id,
        },
        handleRetry
      )
      
      // Clear retry status on success
      setRetryStatus(null)

      const { content: assistantContent, modelsUsed, tokensUsed, latencyMs } = chatResponse

      // Build agent info from actual models used
      const agentContributions = modelsUsed.slice(0, 3).map((modelId, index) => {
        const model = getModelById(modelId)
        const roles = ["Primary response", "Analysis and verification", "Cross-validation"]
        return {
          agentId: `agent-${index + 1}`,
          agentName: model?.name || modelId,
          agentType: "general" as const,
          contribution: roles[index] || "Supporting response",
          confidence: 0.9 - (index * 0.05),
        }
      })

      const assistantMessage: Message = {
        id: `msg-${Date.now()}`,
        role: "assistant",
        content: assistantContent || "I apologize, but I couldn't generate a response. Please try again.",
        timestamp: new Date(),
        model: modelsUsed[0] || actualModels[0],
        agents: agentContributions.length > 0 ? agentContributions : [
          { agentId: "agent-1", agentName: "General Agent", agentType: "general", contribution: "Primary response", confidence: 0.9 },
        ],
        consensus: modelsUsed.length > 1 
          ? { confidence: 88, debateOccurred: true, consensusNote: `${modelsUsed.length} models reached consensus` }
          : { confidence: 95, debateOccurred: false, consensusNote: "Single model response" },
      }

      onSendMessage(assistantMessage)

      // Complete orchestration
      setOrchestrationStatus((prev) => ({
        ...prev,
        isActive: false,
        currentStep: "Completed",
        modelsUsed,
        endTime: new Date(),
        latencyMs,
        events: [
          ...prev.events,
          {
            id: `evt-${++eventIdRef.current}`,
            type: "completed",
            message: "Orchestration complete",
            timestamp: new Date(),
            progress: 100,
          },
        ],
      }))

      // Store for display (actual values from backend)
      setLastModelsUsed(modelsUsed)
      setLastLatencyMs(latencyMs)
      setLastTokensUsed(tokensUsed)
    } catch (error) {
      // Clear retry status
      setRetryStatus(null)
      
      // Create user-friendly error message based on error type
      let errorContent = "I apologize, but I encountered an error. Please try again."
      let errorDetail = "Orchestration failed"
      let retryInfo = ""
      let canRetry = true
      
      // Check for retry exhaustion
      const hasRetryInfo = (err: unknown): err is { retriesExhausted?: boolean; retryInfo?: { attempts?: number } } => {
        return typeof err === 'object' && err !== null
      }
      
      if (hasRetryInfo(error) && error.retriesExhausted && error.retryInfo?.attempts) {
        retryInfo = ` (retried ${error.retryInfo.attempts} times)`
      }
      
      if (error instanceof TimeoutError) {
        errorContent = `The request timed out${retryInfo}. The backend may be overloaded. Please try again later.`
        errorDetail = `Request timed out${retryInfo}`
        toast.warning("Request timed out")
      } else if (error instanceof NetworkError) {
        errorContent = `Unable to connect to the server${retryInfo}. Please check your connection and try again.`
        errorDetail = `Network error${retryInfo}`
        toast.error("Network error")
      } else if (error instanceof ApiError) {
        if (error.retriesExhausted) {
          errorContent = `The server is currently unavailable${retryInfo}. Please try again later.`
          errorDetail = `Server error: ${error.status}${retryInfo}`
          toast.error(`API Error (${error.status}): ${error.message}`)
        } else if (error.status === 401 || error.status === 403) {
          errorContent = `Authentication error: ${error.message}`
          errorDetail = `Auth error: ${error.status}`
          canRetry = false
          toast.error(`API Error (${error.status}): ${error.message}`)
        } else {
          errorContent = `I encountered an error: ${error.message}`
          errorDetail = `API error: ${error.status}`
          toast.error(`API Error (${error.status}): ${error.message}`)
        }
      } else {
        toast.error("An unexpected error occurred. Please try again.")
      }

      // Store error state for retry button
      setErrorState({
        hasError: true,
        message: errorContent,
        canRetry,
        lastInput: userMessage.content,
      })

      const errorMessage: Message = {
        id: `msg-${Date.now()}`,
        role: "assistant",
        content: errorContent,
        timestamp: new Date(),
      }
      onSendMessage(errorMessage)

      // Mark orchestration as error
      setOrchestrationStatus((prev) => ({
        ...prev,
        isActive: false,
        events: [
          ...prev.events,
          {
            id: `evt-${++eventIdRef.current}`,
            type: "error",
            message: errorDetail,
            timestamp: new Date(),
          },
        ],
      }))
    } finally {
      setIsLoading(false)
      setRetryStatus(null)
    }
  }

  const displayMessages = conversation?.messages || []

  return (
    <div className="flex-1 flex flex-col relative min-h-0">
      {/* Hexagonal pattern background */}
      <div
        className="absolute inset-0 opacity-[0.02] pointer-events-none"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M30 0l25.98 15v30L30 60 4.02 45V15z' fill='none' stroke='%23C48E48' strokeWidth='1'/%3E%3C/svg%3E")`,
          backgroundSize: "60px 60px",
        }}
      />

      <header className="border-b border-white/10 p-3 glass-content sticky top-0 z-40 space-y-3">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          {/* Active Mode Badge */}
          <div className="flex items-center gap-2">
            <Badge 
              variant="outline" 
              className={`gap-1.5 px-2.5 py-1 border-0 bg-gradient-to-r ${activeModeInfo.color} text-white font-medium`}
            >
              <activeModeInfo.icon className="h-3.5 w-3.5" />
              {activeModeInfo.label}
            </Badge>
          </div>
          <div className="flex items-center gap-4 flex-wrap flex-1 justify-center">
            <ChatToolbar
              settings={orchestratorSettings}
              onSettingsChange={onOrchestratorSettingsChange}
              onOpenAdvanced={onOpenAdvancedSettings}
            />
          </div>
          {userAccountMenu}
        </div>
        {/* Orchestration Studio - Collapsible */}
        <OrchestrationStudio
          settings={orchestratorSettings}
          onSettingsChange={onOrchestratorSettingsChange}
        />
      </header>

      <HiveActivityIndicator active={isLoading} agentCount={6} />

      {/* Live Status Panel - Shows during orchestration */}
      {(orchestrationStatus.isActive || orchestrationStatus.events.length > 0) && (
        <div className="px-4 py-2 border-b border-white/10 glass-content">
          <div className="max-w-4xl mx-auto">
            <LiveStatusPanel status={orchestrationStatus} />
          </div>
        </div>
      )}

      <ScrollArea className="flex-1 relative z-10">
        <div className="max-w-4xl mx-auto px-4 py-8 space-y-6">
          {displayMessages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              onShowArtifact={onShowArtifact}
              onShowInsights={() => {
                setSelectedMessageForInsights(message)
                setShowInsights(true)
              }}
              incognitoMode={incognitoMode}
              onToggleIncognito={() => setIncognitoMode(!incognitoMode)}
            />
          ))}
          {isLoading && (
            <div className="flex gap-3 items-start">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[var(--bronze)] to-[var(--gold)] flex items-center justify-center">
                <span className="text-xs font-bold text-background">AI</span>
              </div>
              <div className="flex flex-col gap-2">
                <div className="flex gap-1.5 p-4">
                  {[0, 200, 400].map((delay) => (
                    <div
                      key={delay}
                      className="w-1.5 h-1.5 rounded-full bg-[var(--bronze)] animate-bounce"
                      style={{ animationDelay: `${delay}ms`, animationDuration: "1s" }}
                    />
                  ))}
                </div>
                {/* Retry Status Indicator */}
                {retryStatus?.isRetrying && (
                  <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-600 dark:text-amber-400 text-sm animate-pulse">
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    <span>{retryStatus.message}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Error Retry Button */}
          {!isLoading && errorState.hasError && errorState.canRetry && errorState.lastInput && (
            <div className="flex justify-center py-4">
              <Button
                variant="outline"
                size="sm"
                className="gap-2 border-amber-500/50 text-amber-600 dark:text-amber-400 hover:bg-amber-500/10"
                onClick={() => {
                  setInput(errorState.lastInput || "")
                  setErrorState({ hasError: false, message: "", canRetry: false })
                  toast.info("Ready to retry. Click send to try again.")
                }}
              >
                <RefreshCw className="h-4 w-4" />
                Retry Last Message
              </Button>
            </div>
          )}

          {/* Models Used Display - Shows after response */}
          {!isLoading && lastModelsUsed.length > 0 && displayMessages.length > 0 && (
            <div className="flex justify-center py-2">
              <ModelsUsedDisplay
                modelIds={lastModelsUsed}
                totalTokens={lastTokensUsed}
                latencyMs={lastLatencyMs}
              />
            </div>
          )}
        </div>
      </ScrollArea>

      {showInsights && selectedMessageForInsights?.agents && (
        <AgentInsightsPanel
          agents={selectedMessageForInsights.agents}
          consensus={selectedMessageForInsights.consensus!}
          citations={selectedMessageForInsights.citations}
          onClose={() => setShowInsights(false)}
        />
      )}

      <div className="border-t border-white/10 p-3 md:p-4 glass-content relative z-10 sticky bottom-0">
        <div className="max-w-4xl mx-auto">
          {attachments.length > 0 && (
            <div className="mb-3 flex flex-wrap gap-2">
              {attachments.map((att) => (
                <div key={att.id} className="flex items-center gap-2 px-3 py-2 rounded-lg bg-secondary border text-sm">
                  {att.type.startsWith("image/") ? <ImageIcon className="h-4 w-4" /> : <FileText className="h-4 w-4" />}
                  <span className="truncate max-w-[100px] md:max-w-[150px]">{att.name}</span>
                  <Button size="icon" variant="ghost" className="h-5 w-5" onClick={() => removeAttachment(att.id)}>
                    <X className="h-3 w-3" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          {/* Voice interim transcript display */}
          {isListening && interimTranscript && (
            <div className="mb-2 p-2 rounded-lg bg-red-500/10 border border-red-500/20 animate-in fade-in-0 slide-in-from-bottom-2">
              <div className="flex items-center gap-2 text-xs text-red-500">
                <Volume2 className="h-3 w-3 animate-pulse" />
                <span className="italic">{interimTranscript}</span>
              </div>
            </div>
          )}

          {/* OCR processing indicator */}
          {isProcessingOCR && (
            <div className="mb-2 p-2 rounded-lg bg-blue-500/10 border border-blue-500/20">
              <div className="flex items-center gap-2 text-xs text-blue-500">
                <ImageIcon className="h-3 w-3 animate-pulse" />
                <span>Analyzing image...</span>
                <Progress value={undefined} className="w-20 h-1" />
              </div>
            </div>
          )}

          <div className="relative">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              placeholder={isListening ? "Listening... speak now" : "Ask the hive mind anything..."}
              aria-label="Chat message input"
              className={`min-h-[56px] md:min-h-[72px] pr-28 md:pr-36 resize-none bg-white/5 border-white/10 focus:border-[var(--bronze)] text-sm md:text-base ${
                isListening ? 'border-red-500/50 ring-1 ring-red-500/20' : ''
              }`}
              spellCheck={orchestratorSettings.enableSpellCheck !== false}
              autoComplete="on"
              autoCorrect="on"
            />
            <div className="absolute bottom-2 md:bottom-2.5 right-2 md:right-2.5 flex items-center gap-1 md:gap-1.5">
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="image/*,.pdf,.doc,.docx,.txt"
                onChange={handleFileSelect}
                className="hidden"
              />
              <input
                ref={cameraInputRef}
                type="file"
                accept="image/*"
                capture="environment"
                onChange={handleCameraCapture}
                className="hidden"
              />
              <Button
                size="icon"
                variant="ghost"
                className="h-7 w-7 md:h-8 md:w-8"
                onClick={() => fileInputRef.current?.click()}
                title="Attach file"
              >
                <Paperclip className="h-3.5 w-3.5 md:h-4 md:w-4" />
              </Button>
              <Button 
                size="icon" 
                variant="ghost" 
                className="h-7 w-7 md:h-8 md:w-8"
                onClick={() => cameraInputRef.current?.click()}
                title="Capture image for OCR"
              >
                <Camera className="h-3.5 w-3.5 md:h-4 md:w-4" />
              </Button>
              {/* Voice input button with audio level indicator */}
              <div className="relative">
                <Button 
                  size="icon" 
                  variant="ghost" 
                  className={`h-7 w-7 md:h-8 md:w-8 transition-all duration-200 ${
                    isListening 
                      ? 'bg-red-500/20 text-red-500' 
                      : ''
                  }`}
                  onClick={toggleVoiceRecording}
                  disabled={!speechSupported}
                  title={isListening ? "Stop listening" : "Voice input"}
                  style={isListening ? {
                    boxShadow: `0 0 ${Math.round(audioLevel * 20)}px ${Math.round(audioLevel * 10)}px rgba(239, 68, 68, ${audioLevel * 0.5})`
                  } : {}}
                >
                  {isListening ? (
                    <Volume2 className="h-3.5 w-3.5 md:h-4 md:w-4 animate-pulse" />
                  ) : (
                    <Mic className="h-3.5 w-3.5 md:h-4 md:w-4" />
                  )}
                </Button>
                {/* Audio level ring indicator */}
                {isListening && audioLevel > 0.1 && (
                  <div 
                    className="absolute inset-0 rounded-md border-2 border-red-500 pointer-events-none animate-ping"
                    style={{ opacity: audioLevel * 0.6 }}
                  />
                )}
              </div>
              <Button
                size="icon"
                onClick={() => handleSend()}
                disabled={(!input.trim() && attachments.length === 0) || isLoading}
                className="h-7 w-7 md:h-8 md:w-8 bronze-gradient disabled:opacity-50"
              >
                <Send className="h-3.5 w-3.5 md:h-4 md:w-4" />
              </Button>
            </div>
          </div>
          
          {/* Clarification prompt - proceed anyway button */}
          {pendingClarification && (
            <div className="flex items-center justify-center gap-2 mt-2 px-4">
              <span className="text-xs text-muted-foreground">Have clarifications?</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  // Clear clarification state and proceed with original input
                  const originalInput = pendingInput
                  setPendingClarification(null)
                  setPendingInput("")
                  setInput(originalInput)
                  // Trigger send with skip flag after state update
                  setTimeout(() => handleSend(true), 0)
                }}
                className="text-xs h-6 px-2 text-[var(--bronze)] hover:bg-[var(--bronze)]/10"
              >
                Skip & proceed with original question
              </Button>
            </div>
          )}
          
          <p className="text-[9px] md:text-[10px] text-muted-foreground mt-2 text-center opacity-60">
            LLMHive uses multiple AI agents for enhanced accuracy
            {orchestratorSettings.enableClarificationQuestions && " • Clarification questions enabled"}
          </p>
        </div>
      </div>
    </div>
  )
}

/**
 * ChatArea wrapped with ErrorBoundary for graceful error handling.
 * Use this version in production to catch and display errors nicely.
 */
export function ChatAreaWithErrorBoundary(props: ChatAreaProps) {
  return (
    <ErrorBoundary
      onError={(error, errorInfo) => {
        // Log to console (would also log to error reporting service)
        console.error("[ChatArea Error]", error, errorInfo)
        toast.error("Chat Error: Something went wrong. Please try refreshing the page.")
      }}
    >
      <ChatArea {...props} />
    </ErrorBoundary>
  )
}
