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
export type DomainPack = "default" | "medical" | "legal" | "marketing" | "coding" | "research" | "finance"
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
  enableHRM: boolean // Hierarchical Role Management
  enablePromptDiffusion: boolean // Prompt Diffusion & Refinement
  enableDeepConsensus: boolean // Deep Consensus (multi-round debate)
  enableAdaptiveEnsemble: boolean // Adaptive Ensemble Logic
  // Dynamic Criteria Equalizer
  criteria?: CriteriaSettings
  // Elite Orchestration settings (new)
  eliteStrategy?: EliteStrategy // Strategy for elite orchestration
  qualityOptions?: QualityOption[] // Quality boosting techniques
  enableToolBroker?: boolean // Automatic tool detection and execution
  enableVerification?: boolean // Tool-based verification for code/math
  enablePromptOps?: boolean // Always-on query preprocessing
  enableAnswerRefiner?: boolean // Always-on answer polishing
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
