/**
 * Type-safe API client for LLMHive frontend.
 * 
 * This module provides typed functions for all API interactions,
 * matching the backend Pydantic models for type safety.
 * 
 * Features:
 * - Exponential backoff retry logic for transient errors
 * - Timeout handling
 * - Type-safe request/response interfaces
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
// Retry Configuration
// ============================================================

export interface RetryConfig {
  /** Maximum number of retry attempts */
  maxRetries: number
  /** Base delay in milliseconds for exponential backoff */
  baseDelayMs: number
  /** Maximum delay in milliseconds */
  maxDelayMs: number
  /** Jitter factor (0-1) to randomize delay */
  jitterFactor: number
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  baseDelayMs: 1000,
  maxDelayMs: 10000,
  jitterFactor: 0.3,
}

const LIGHT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 2,
  baseDelayMs: 500,
  maxDelayMs: 5000,
  jitterFactor: 0.2,
}

// ============================================================
// Error Types
// ============================================================

export interface RetryInfo {
  /** Number of retry attempts made */
  attempts: number
  /** Whether all retries have been exhausted */
  retriesExhausted: boolean
  /** Total time spent on retries in ms */
  totalRetryTimeMs: number
  /** Last error that caused retry */
  lastError?: string
}

export class ApiError extends Error {
  public retryInfo?: RetryInfo

  constructor(
    message: string,
    public status: number,
    public code?: string,
    public details?: unknown,
    retryInfo?: RetryInfo
  ) {
    super(message)
    this.name = "ApiError"
    this.retryInfo = retryInfo
  }

  /** Whether this error exhausted all retry attempts */
  get retriesExhausted(): boolean {
    return this.retryInfo?.retriesExhausted ?? false
  }
}

export class NetworkError extends Error {
  public retryInfo?: RetryInfo

  constructor(message: string, public cause?: Error, retryInfo?: RetryInfo) {
    super(message)
    this.name = "NetworkError"
    this.retryInfo = retryInfo
  }

  get retriesExhausted(): boolean {
    return this.retryInfo?.retriesExhausted ?? false
  }
}

export class TimeoutError extends Error {
  public retryInfo?: RetryInfo

  constructor(message: string = "Request timed out", retryInfo?: RetryInfo) {
    super(message)
    this.name = "TimeoutError"
    this.retryInfo = retryInfo
  }

  get retriesExhausted(): boolean {
    return this.retryInfo?.retriesExhausted ?? false
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
  /** Retry information if retries were attempted */
  retryInfo?: RetryInfo
}

// ============================================================
// Retry Utility Functions
// ============================================================

/**
 * Calculate delay with exponential backoff and jitter.
 * 
 * @param attempt - Current attempt number (0-based)
 * @param config - Retry configuration
 * @returns Delay in milliseconds
 */
function calculateBackoffDelay(attempt: number, config: RetryConfig): number {
  // Exponential backoff: baseDelay * 2^attempt
  const exponentialDelay = config.baseDelayMs * Math.pow(2, attempt)
  
  // Cap at max delay
  const cappedDelay = Math.min(exponentialDelay, config.maxDelayMs)
  
  // Add jitter to prevent thundering herd
  const jitter = cappedDelay * config.jitterFactor * Math.random()
  
  return Math.floor(cappedDelay + jitter)
}

/**
 * Check if an error is retryable.
 * 
 * Only retry on:
 * - 5xx server errors
 * - Network errors
 * - Timeout errors
 * - 429 (rate limit)
 * 
 * Don't retry on:
 * - 4xx client errors (except 429)
 * - Successful responses
 */
function isRetryableError(error: unknown): boolean {
  if (error instanceof TimeoutError) {
    return true
  }
  
  if (error instanceof NetworkError) {
    return true
  }
  
  if (error instanceof ApiError) {
    // 5xx server errors are retryable
    if (error.status >= 500 && error.status < 600) {
      return true
    }
    // 429 rate limit is retryable
    if (error.status === 429) {
      return true
    }
    // 4xx client errors are NOT retryable
    return false
  }
  
  // Unknown errors - retry to be safe
  return true
}

/**
 * Sleep for a specified duration.
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * Callback for retry status updates.
 */
export type RetryStatusCallback = (status: {
  attempt: number
  maxAttempts: number
  delayMs: number
  error: string
}) => void

/**
 * Execute a function with retry logic.
 * 
 * @param fn - Async function to execute
 * @param config - Retry configuration
 * @param onRetry - Optional callback for retry status updates
 * @returns Result of the function
 * @throws Original error with retry info if all retries fail
 */
async function withRetry<T>(
  fn: () => Promise<T>,
  config: RetryConfig = DEFAULT_RETRY_CONFIG,
  onRetry?: RetryStatusCallback
): Promise<{ result: T; retryInfo: RetryInfo }> {
  const startTime = Date.now()
  let lastError: Error | undefined
  let attempts = 0
  
  while (attempts <= config.maxRetries) {
    try {
      const result = await fn()
      return {
        result,
        retryInfo: {
          attempts,
          retriesExhausted: false,
          totalRetryTimeMs: Date.now() - startTime,
        },
      }
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error))
      attempts++
      
      // Check if we should retry
      if (attempts > config.maxRetries || !isRetryableError(error)) {
        // Don't retry - throw with retry info
        const retryInfo: RetryInfo = {
          attempts: attempts - 1, // Subtract 1 because we incremented before checking
          retriesExhausted: attempts > config.maxRetries,
          totalRetryTimeMs: Date.now() - startTime,
          lastError: lastError.message,
        }
        
        // Add retry info to the error
        if (error instanceof ApiError) {
          error.retryInfo = retryInfo
        } else if (error instanceof NetworkError) {
          error.retryInfo = retryInfo
        } else if (error instanceof TimeoutError) {
          error.retryInfo = retryInfo
        }
        
        throw error
      }
      
      // Calculate delay and wait
      const delay = calculateBackoffDelay(attempts - 1, config)
      
      // Notify about retry
      if (onRetry) {
        onRetry({
          attempt: attempts,
          maxAttempts: config.maxRetries + 1,
          delayMs: delay,
          error: lastError.message,
        })
      }
      
      await sleep(delay)
    }
  }
  
  // Should never reach here, but just in case
  throw lastError
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
 * Uses exponential backoff retry (up to 3 retries) for transient errors.
 * 
 * @param request - Chat request containing messages, models, and settings
 * @param onRetry - Optional callback for retry status updates
 * @returns Chat response with content, models used, metrics, and retry info
 * @throws ApiError if the request fails
 * @throws NetworkError if unable to connect
 * @throws TimeoutError if the request times out
 */
export async function sendChat(
  request: ChatRequest,
  onRetry?: RetryStatusCallback
): Promise<ChatResponse> {
  const { result, retryInfo } = await withRetry(
    async () => {
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
    },
    DEFAULT_RETRY_CONFIG, // Up to 3 retries for chat
    onRetry
  )

  return {
    ...result,
    retryInfo,
  }
}

/**
 * Save user settings.
 * 
 * Uses exponential backoff retry (up to 2 retries) for transient errors.
 * 
 * @param settings - Settings to save
 * @throws ApiError if the request fails
 */
export async function saveSettings(settings: SettingsRequest): Promise<void> {
  await withRetry(
    async () => {
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
    },
    LIGHT_RETRY_CONFIG // Up to 2 retries
  )
}

/**
 * Load user settings.
 * 
 * Uses exponential backoff retry (up to 2 retries) for transient errors.
 * 
 * @param userId - User ID to load settings for
 * @returns Settings response
 * @throws ApiError if the request fails
 */
export async function loadSettings(userId: string = "default"): Promise<SettingsResponse> {
  const url = `${API_ROUTES.SETTINGS}?userId=${encodeURIComponent(userId)}`
  
  const { result } = await withRetry(
    async () => {
      const response = await fetchWithTimeout(url, { method: "GET" }, 10000)

      if (!response.ok) {
        throw await parseErrorResponse(response)
      }

      return response.json()
    },
    LIGHT_RETRY_CONFIG
  )

  return result
}

/**
 * Save criteria settings.
 * 
 * Uses exponential backoff retry (up to 2 retries) for transient errors.
 * 
 * @param criteria - Criteria settings to save
 * @param userId - Optional user ID
 * @throws ApiError if the request fails
 */
export async function saveCriteria(
  criteria: CriteriaSettings,
  userId: string = "default"
): Promise<void> {
  await withRetry(
    async () => {
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
    },
    LIGHT_RETRY_CONFIG
  )
}

/**
 * Load criteria settings.
 * 
 * Uses exponential backoff retry (up to 2 retries) for transient errors.
 * 
 * @param userId - User ID to load criteria for
 * @returns Criteria settings
 * @throws ApiError if the request fails
 */
export async function loadCriteria(userId: string = "default"): Promise<CriteriaSettings> {
  const url = `${API_ROUTES.CRITERIA}?userId=${encodeURIComponent(userId)}`
  
  const { result } = await withRetry(
    async () => {
      const response = await fetchWithTimeout(url, { method: "GET" }, 10000)

      if (!response.ok) {
        throw await parseErrorResponse(response)
      }

      const data: CriteriaResponse = await response.json()
      return data.settings
    },
    LIGHT_RETRY_CONFIG
  )

  return result
}

/**
 * Execute code via the backend.
 * 
 * Uses exponential backoff retry (up to 2 retries) for transient errors.
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
  const { result } = await withRetry(
    async () => {
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
    },
    LIGHT_RETRY_CONFIG
  )

  return result
}

/**
 * Get available agents/models.
 * 
 * Uses exponential backoff retry (up to 2 retries) for transient errors.
 * 
 * @returns List of available agents with their status
 */
export async function getAgents(): Promise<Array<{
  id: string
  name: string
  provider: string
  available: boolean
}>> {
  const { result } = await withRetry(
    async () => {
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
    },
    LIGHT_RETRY_CONFIG
  )

  return result
}

/**
 * Save reasoning configuration.
 * 
 * Uses exponential backoff retry (up to 2 retries) for transient errors.
 * 
 * @param mode - Reasoning mode (auto or manual)
 * @param selectedMethods - Selected reasoning methods for manual mode
 */
export async function saveReasoningConfig(
  mode: "auto" | "manual",
  selectedMethods: string[] = []
): Promise<void> {
  await withRetry(
    async () => {
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
    },
    LIGHT_RETRY_CONFIG
  )
}

/**
 * Load reasoning configuration.
 * 
 * Uses exponential backoff retry (up to 2 retries) for transient errors.
 * 
 * @returns Current reasoning configuration
 */
export async function loadReasoningConfig(): Promise<{
  mode: "auto" | "manual"
  selectedMethods: string[]
}> {
  const { result } = await withRetry(
    async () => {
      const response = await fetchWithTimeout(
        API_ROUTES.REASONING_CONFIG,
        { method: "GET" },
        10000
      )

      if (!response.ok) {
        throw await parseErrorResponse(response)
      }

      return response.json()
    },
    LIGHT_RETRY_CONFIG
  )

  return result
}
