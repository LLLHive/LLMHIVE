/** Quality metadata for AI response tracking and debugging */
export interface QualityMetadata {
  traceId?: string
  confidence?: number
  confidenceLabel?: string
  modelsUsed?: string[]
  strategyUsed?: string
  verificationStatus?: string
  verificationScore?: number
  toolsUsed?: string[]
  ragUsed?: boolean
  memoryUsed?: boolean
  sources?: Array<{ title: string; url?: string }>
  isStub?: boolean
  selfGraded?: boolean
  improvementApplied?: boolean
  // Extended fields for full orchestration metadata
  issuesFound?: number
  correctionsApplied?: boolean
  eliteStrategy?: string
  consensusScore?: number
  taskType?: string
  cached?: boolean
}

export interface Message {
  id: string
  role: "user" | "assistant" | "system"
  content: string
  timestamp: Date
  model?: string
  reasoning?: {
    mode: "deep" | "standard" | "fast"
    steps?: string[]
  }
  attachments?: Attachment[]
  artifact?: Artifact
  agents?: AgentContribution[]
  consensus?: ConsensusInfo
  citations?: Citation[]
  isProcessing?: boolean
  isClarificationRequest?: boolean
  isRegenerated?: boolean
  modelsUsed?: string[]
  metadata?: Record<string, unknown>
  /** Quality metadata for "Why this answer?" drawer */
  qualityMetadata?: QualityMetadata
}

export interface Attachment {
  id: string
  name: string
  type: string
  size: number
  url: string
}

export interface Artifact {
  id: string
  type: "code" | "document" | "visualization"
  title: string
  content: string
  language?: string
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  createdAt: Date
  updatedAt: Date
  model: string
  pinned?: boolean
  archived?: boolean
  projectId?: string
}

export interface Project {
  id: string
  name: string
  description: string
  conversations: string[]
  files: ProjectFile[]
  createdAt: Date
}

export interface ProjectFile {
  id: string
  name: string
  content: string
  type: string
}

export type ModelProvider = "openai" | "anthropic" | "google" | "xai" | "deepseek" | "meta" | "orchestrator"

export interface Model {
  id: string
  name: string
  provider: ModelProvider
  description?: string
  capabilities: {
    vision: boolean
    codeExecution: boolean
    webSearch: boolean
    reasoning: boolean
  }
}

export interface AgentContribution {
  agentId: string
  agentName: string
  agentType: "legal" | "code" | "research" | "math" | "creative" | "general"
  contribution: string
  confidence: number
  citations?: Citation[]
}

export interface Citation {
  id: string
  text: string
  source: string
  url: string
  verified: boolean
}

export interface ConsensusInfo {
  confidence: number
  debateOccurred: boolean
  consensusNote?: string
}

export interface CriteriaSettings {
  accuracy: number // 0-100
  speed: number // 0-100
  creativity: number // 0-100
}

export interface Integration {
  id: string
  name: "github" | "google-cloud" | "vercel"
  connected: boolean
  config?: Record<string, any>
}

export type ReasoningMode = "fast" | "standard" | "deep"
export type DomainPack = "default" | "medical" | "legal" | "marketing" | "coding" | "research" | "finance" | "education" | "real_estate" | "creative"
export type AgentMode = "single" | "team"
export type AdvancedReasoningMethod =
  | "automatic"
  | "chain-of-thought"
  | "tree-of-thought"
  | "self-consistency"
  | "react"
  | "reflexion"
  | "least-to-most"
  | "plan-and-solve"
  | "graph-of-thought"
  | "algorithm-of-thought"
  | "skeleton-of-thought"
  | "cumulative-reasoning"
  | "meta-prompting"

export type AdvancedFeature =
  | "vector-rag"
  | "mcp-server"
  | "personal-database"
  | "modular-answer-feed"
  | "memory-augmentation"
  | "tool-use"
  | "code-interpreter"

export type EliteStrategy =
  | "automatic"
  | "single_best"
  | "parallel_race"
  | "best_of_n"
  | "quality_weighted_fusion"
  | "expert_panel"
  | "challenge_and_refine"

export type QualityOption =
  | "verification"
  | "consensus"
  | "chain_of_thought"
  | "self_consistency"
  | "reflection"
  | "decomposition"

export interface StandardLLMSettings {
  temperature: number // 0-2, default 0.7
  maxTokens: number // 100-4000, default 2000
  topP: number // 0-1, default 0.9
  frequencyPenalty: number // 0-2, default 0
  presencePenalty: number // 0-2, default 0
}

export type AnswerFormat = 
  | "automatic"  // Automatically select best format based on prompt/answer
  | "default"
  | "structured"
  | "bullet-points"
  | "step-by-step"
  | "academic"
  | "concise"

export interface OrchestratorSettings {
  reasoningMode: ReasoningMode
  domainPack: DomainPack
  agentMode: AgentMode
  promptOptimization: boolean
  outputValidation: boolean
  answerStructure: boolean
  sharedMemory: boolean
  learnFromChat: boolean
  selectedModels: string[]
  advancedReasoningMethods: AdvancedReasoningMethod[]
  advancedFeatures: AdvancedFeature[]
  // Orchestration Studio settings
  accuracyLevel: number // 1-5 slider (1=fastest, 5=most accurate)
  enginesMode: "automatic" | "manual" // Automatic selects best engines based on prompt
  enableHRM: boolean // Hierarchical Role Management
  enablePromptDiffusion: boolean // Prompt Diffusion & Refinement
  enableDeepConsensus: boolean // Deep Consensus (multi-round debate)
  enableAdaptiveEnsemble: boolean // Adaptive Ensemble Logic
  // Dynamic Criteria Equalizer
  criteria?: CriteriaSettings
  // Elite Orchestration settings
  eliteStrategy?: EliteStrategy // Strategy for elite orchestration
  qualityOptions?: QualityOption[] // Quality boosting techniques
  enableToolBroker?: boolean // Automatic tool detection and execution
  enableVerification?: boolean // Tool-based verification for code/math
  enablePromptOps?: boolean // Always-on query preprocessing
  enableAnswerRefiner?: boolean // Always-on answer polishing
  // Standard LLM parameters (sent to backend)
  standardValues?: StandardLLMSettings
  // UI/UX settings
  enableSpellCheck?: boolean // Enable spell check in chat input
  // PR5 & PR6: Budget-aware routing
  maxCostUsd?: number // Maximum cost per request in USD
  preferCheaper?: boolean // Prefer cheaper models
  // PR6: Orchestration overrides
  modelTeam?: Array<{
    modelId: string
    role: 'primary' | 'validator' | 'fallback' | 'specialist'
    weight?: number
  }> // Custom model team with roles
  orchestrationOverrides?: {
    strategy?: EliteStrategy
    enableRefinement?: boolean
    enableVerification?: boolean
    maxIterations?: number
  }
  answerFormat?: AnswerFormat // Answer structure format preference
  enableClarificationQuestions?: boolean // Ask clarifying questions before answering
  enableLiveResearch?: boolean // Enable real-time web search for current data
}

// Clarification question from the AI
export interface ClarificationQuestion {
  id: string
  question: string
  options?: string[] // Optional pre-defined answer options
  type: 'text' | 'choice' | 'confirmation'
}

// Orchestration status event types
export type OrchestrationEventType =
  | "started"
  | "refining_prompt"
  | "dispatching_model"
  | "model_responding"
  | "model_critiquing"
  | "verifying_facts"
  | "consensus_building"
  | "finalizing"
  | "completed"
  | "error"

export interface OrchestrationEvent {
  id: string
  type: OrchestrationEventType
  message: string
  timestamp: Date
  modelName?: string
  progress?: number // 0-100
  details?: string
}

export interface OrchestrationStatus {
  isActive: boolean
  currentStep: string
  events: OrchestrationEvent[]
  modelsUsed: string[]
  startTime?: Date
  endTime?: Date
  totalTokens?: number
  latencyMs?: number
}

export interface ChatTemplate {
  id: string
  title: string
  description: string
  icon: string
  preset: Partial<OrchestratorSettings>
}
