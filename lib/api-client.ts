/**
 * Type-safe API client for LLMHive frontend.
 * 
 * This module provides typed functions for all API interactions,
 * matching the backend Pydantic models for type safety.
 */

import { API_ROUTES } from "./routes"
import type { 
  Message, 
  OrchestratorSettings, 
  CriteriaSettings,
  ReasoningMode,
  DomainPack,
  AgentMode,
} from "./types"

// ============================================================
// Error Types
// ============================================================

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public details?: unknown
  ) {
    super(message)
    this.name = "ApiError"
  }
}

export class NetworkError extends Error {
  constructor(message: string, public cause?: Error) {
    super(message)
    this.name = "NetworkError"
  }
}

export class TimeoutError extends Error {
  constructor(message: string = "Request timed out") {
    super(message)
    this.name = "TimeoutError"
  }
}

// ============================================================
// Request/Response Types (matching backend Pydantic models)
// ============================================================

export interface TuningOptions {
  prompt_optimization: boolean
  output_validation: boolean
  answer_structure: boolean
  learn_from_chat: boolean
}

export interface OrchestrationSettingsRequest {
  accuracy_level?: number
  enable_hrm?: boolean
  enable_prompt_diffusion?: boolean
  enable_deep_consensus?: boolean
  enable_adaptive_ensemble?: boolean
  elite_strategy?: string
  quality_options?: string[]
  temperature?: number
  max_tokens?: number
  top_p?: number
  frequency_penalty?: number
  presence_penalty?: number
  enable_tool_broker?: boolean
  enable_verification?: boolean
  enable_vector_rag?: boolean
  enable_memory?: boolean
}

export interface ChatMetadata {
  chat_id?: string
  user_id?: string
  project_id?: string
  criteria?: CriteriaSettings
}

export interface ChatRequestPayload {
  prompt: string
  models?: string[]
  reasoning_mode?: ReasoningMode
  reasoning_method?: string
  domain_pack?: DomainPack
  agent_mode?: AgentMode
  tuning?: TuningOptions
  orchestration?: OrchestrationSettingsRequest
  metadata?: ChatMetadata
  history?: Array<{ role: string; content: string }>
}

export interface AgentTrace {
  agent_id?: string
  agent_name?: string
  contribution?: string
  confidence?: number
  timestamp?: number
}

export interface ChatResponsePayload {
  message: string
  models_used: string[]
  reasoning_mode: ReasoningMode
  reasoning_method?: string
  domain_pack: DomainPack
  agent_mode: AgentMode
  used_tuning: TuningOptions
  metadata: ChatMetadata
  tokens_used?: number
  latency_ms?: number
  agent_traces: AgentTrace[]
  extra: Record<string, unknown>
}

export interface SettingsRequest {
  userId?: string
  orchestratorSettings?: Partial<OrchestratorSettings>
  criteriaSettings?: CriteriaSettings
  preferences?: {
    incognitoMode?: boolean
    theme?: string
    language?: string
  }
}

export interface SettingsResponse {
  success: boolean
  settings: {
    orchestratorSettings: {
      reasoningMode: string
      domainPack: string
      agentMode: string
      promptOptimization: boolean
      outputValidation: boolean
      answerStructure: boolean
      sharedMemory: boolean
      learnFromChat: boolean
      selectedModels: string[]
      advancedReasoningMethods: string[]
      advancedFeatures: string[]
    }
    criteriaSettings: CriteriaSettings
    preferences: {
      incognitoMode: boolean
      theme: string
      language: string
    }
  }
}

export interface CriteriaResponse {
  success: boolean
  settings: CriteriaSettings
}

// ============================================================
// Chat API Request (simplified for frontend use)
// ============================================================

export interface ChatRequest {
  messages: Message[]
  models: string[]
  orchestratorSettings: OrchestratorSettings
  chatId?: string
  userId?: string
  projectId?: string
}

export interface ChatResponse {
  content: string
  modelsUsed: string[]
  tokensUsed: number
  latencyMs: number
}

// ============================================================
// Helper Functions
// ============================================================

/**
 * Convert frontend OrchestratorSettings to backend format.
 */
function toBackendOrchestrationSettings(
  settings: OrchestratorSettings
): OrchestrationSettingsRequest {
  return {
    accuracy_level: settings.accuracyLevel,
    enable_hrm: settings.enableHRM,
    enable_prompt_diffusion: settings.enablePromptDiffusion,
    enable_deep_consensus: settings.enableDeepConsensus,
    enable_adaptive_ensemble: settings.enableAdaptiveEnsemble,
    elite_strategy: settings.eliteStrategy,
    quality_options: settings.qualityOptions,
    temperature: settings.standardValues?.temperature,
    max_tokens: settings.standardValues?.maxTokens,
    top_p: settings.standardValues?.topP,
    frequency_penalty: settings.standardValues?.frequencyPenalty,
    presence_penalty: settings.standardValues?.presencePenalty,
    enable_tool_broker: settings.enableToolBroker,
    enable_verification: settings.enableVerification,
    enable_vector_rag: settings.advancedFeatures?.includes("vector-rag"),
    enable_memory: settings.advancedFeatures?.includes("memory-augmentation"),
  }
}

/**
 * Parse error response from API.
 */
async function parseErrorResponse(response: Response): Promise<ApiError> {
  try {
    const data = await response.json()
    return new ApiError(
      data.error || data.detail || `Request failed: ${response.status}`,
      response.status,
      data.code,
      data
    )
  } catch {
    return new ApiError(
      `Request failed: ${response.status} ${response.statusText}`,
      response.status
    )
  }
}

/**
 * Make a fetch request with timeout and error handling.
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs: number = 120000
): Promise<Response> {
  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    })
    return response
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") {
      throw new TimeoutError()
    }
    throw new NetworkError(
      "Failed to connect to server",
      error instanceof Error ? error : undefined
    )
  } finally {
    clearTimeout(timeoutId)
  }
}

// ============================================================
// API Functions
// ============================================================

/**
 * Send a chat message and get a response.
 * 
 * @param request - Chat request containing messages, models, and settings
 * @returns Chat response with content, models used, and metrics
 * @throws ApiError if the request fails
 * @throws NetworkError if unable to connect
 * @throws TimeoutError if the request times out
 */
export async function sendChat(request: ChatRequest): Promise<ChatResponse> {
  const startTime = Date.now()

  const response = await fetchWithTimeout(
    API_ROUTES.CHAT,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages: request.messages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
        models: request.models,
        model: request.models[0],
        orchestratorSettings: {
          ...request.orchestratorSettings,
          selectedModels: request.models,
        },
        chatId: request.chatId,
        userId: request.userId,
        projectId: request.projectId,
      }),
    },
    120000 // 2 minute timeout for chat
  )

  if (!response.ok) {
    throw await parseErrorResponse(response)
  }

  // Extract metadata from headers
  const modelsUsedHeader = response.headers.get("X-Models-Used")
  const tokensUsedHeader = response.headers.get("X-Tokens-Used")
  const backendLatencyHeader = response.headers.get("X-Latency-Ms")

  // Parse models used
  let modelsUsed: string[] = request.models
  if (modelsUsedHeader) {
    try {
      const parsed = JSON.parse(modelsUsedHeader)
      const filtered = parsed.filter((m: string) => m && m !== "automatic")
      if (filtered.length > 0) modelsUsed = filtered
    } catch {
      // Keep default
    }
  }

  // Read response body
  const reader = response.body?.getReader()
  const decoder = new TextDecoder()
  let content = ""

  if (reader) {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      content += decoder.decode(value)
    }
  }

  const tokensUsed = tokensUsedHeader ? parseInt(tokensUsedHeader, 10) : 0
  const latencyMs = backendLatencyHeader
    ? parseInt(backendLatencyHeader, 10)
    : Date.now() - startTime

  return {
    content: content || "I apologize, but I couldn't generate a response.",
    modelsUsed,
    tokensUsed,
    latencyMs,
  }
}

/**
 * Save user settings.
 * 
 * @param settings - Settings to save
 * @throws ApiError if the request fails
 */
export async function saveSettings(settings: SettingsRequest): Promise<void> {
  const response = await fetchWithTimeout(
    API_ROUTES.SETTINGS,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings),
    },
    10000
  )

  if (!response.ok) {
    throw await parseErrorResponse(response)
  }
}

/**
 * Load user settings.
 * 
 * @param userId - User ID to load settings for
 * @returns Settings response
 * @throws ApiError if the request fails
 */
export async function loadSettings(userId: string = "default"): Promise<SettingsResponse> {
  const url = `${API_ROUTES.SETTINGS}?userId=${encodeURIComponent(userId)}`
  
  const response = await fetchWithTimeout(url, { method: "GET" }, 10000)

  if (!response.ok) {
    throw await parseErrorResponse(response)
  }

  return response.json()
}

/**
 * Save criteria settings.
 * 
 * @param criteria - Criteria settings to save
 * @param userId - Optional user ID
 * @throws ApiError if the request fails
 */
export async function saveCriteria(
  criteria: CriteriaSettings,
  userId: string = "default"
): Promise<void> {
  const response = await fetchWithTimeout(
    API_ROUTES.CRITERIA,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        userId,
        accuracy: criteria.accuracy,
        speed: criteria.speed,
        creativity: criteria.creativity,
      }),
    },
    10000
  )

  if (!response.ok) {
    throw await parseErrorResponse(response)
  }
}

/**
 * Load criteria settings.
 * 
 * @param userId - User ID to load criteria for
 * @returns Criteria settings
 * @throws ApiError if the request fails
 */
export async function loadCriteria(userId: string = "default"): Promise<CriteriaSettings> {
  const url = `${API_ROUTES.CRITERIA}?userId=${encodeURIComponent(userId)}`
  
  const response = await fetchWithTimeout(url, { method: "GET" }, 10000)

  if (!response.ok) {
    throw await parseErrorResponse(response)
  }

  const data: CriteriaResponse = await response.json()
  return data.settings
}

/**
 * Execute code via the backend.
 * 
 * @param code - Code to execute
 * @param language - Programming language (default: python)
 * @returns Execution result
 * @throws ApiError if the request fails
 */
export async function executeCode(
  code: string,
  language: string = "python"
): Promise<{ stdout: string; stderr: string; exitCode: number }> {
  const response = await fetchWithTimeout(
    API_ROUTES.EXECUTE,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, language }),
    },
    30000 // 30 second timeout for code execution
  )

  if (!response.ok) {
    throw await parseErrorResponse(response)
  }

  return response.json()
}

/**
 * Get available agents/models.
 * 
 * @returns List of available agents with their status
 */
export async function getAgents(): Promise<Array<{
  id: string
  name: string
  provider: string
  available: boolean
}>> {
  const response = await fetchWithTimeout(
    API_ROUTES.AGENTS,
    { method: "GET" },
    10000
  )

  if (!response.ok) {
    throw await parseErrorResponse(response)
  }

  const data = await response.json()
  return data.agents || []
}

/**
 * Save reasoning configuration.
 * 
 * @param mode - Reasoning mode (auto or manual)
 * @param selectedMethods - Selected reasoning methods for manual mode
 */
export async function saveReasoningConfig(
  mode: "auto" | "manual",
  selectedMethods: string[] = []
): Promise<void> {
  const response = await fetchWithTimeout(
    API_ROUTES.REASONING_CONFIG,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode, selectedMethods }),
    },
    10000
  )

  if (!response.ok) {
    throw await parseErrorResponse(response)
  }
}

/**
 * Load reasoning configuration.
 * 
 * @returns Current reasoning configuration
 */
export async function loadReasoningConfig(): Promise<{
  mode: "auto" | "manual"
  selectedMethods: string[]
}> {
  const response = await fetchWithTimeout(
    API_ROUTES.REASONING_CONFIG,
    { method: "GET" },
    10000
  )

  if (!response.ok) {
    throw await parseErrorResponse(response)
  }

  return response.json()
}
