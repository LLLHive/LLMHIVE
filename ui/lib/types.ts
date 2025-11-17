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
  // New orchestration metadata surfaced from backend
  qualityScore?: number
  confidence?: number
  factCheckSummary?: string
  refinementRounds?: number
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
  backendConversationId?: number
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

export type ModelProvider = "openai" | "anthropic" | "google" | "xai" | "meta"

export interface Model {
  id: string
  name: string
  provider: ModelProvider
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
