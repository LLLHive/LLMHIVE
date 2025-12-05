/**
 * Auto-generated TypeScript types from Pydantic models.
 * 
 * DO NOT EDIT MANUALLY - regenerate with:
 *   cd llmhive && python scripts/generate_types.py -o ../lib/api-types.ts
 * 
 * Generated from: llmhive/src/llmhive/app/models/orchestration.py
 */

/* eslint-disable @typescript-eslint/no-explicit-any */

// ============================================================
// Enums
// ============================================================

export type ReasoningMode =
  | "fast"
  | "standard"
  | "deep"

export type ReasoningMethod =
  | "chain-of-thought"
  | "tree-of-thought"
  | "react"
  | "plan-and-solve"
  | "self-consistency"
  | "reflexion"
  | "hierarchical-decomposition"
  | "iterative-refinement"
  | "confidence-filtering"
  | "dynamic-planning"

export type DomainPack =
  | "default"
  | "medical"
  | "legal"
  | "marketing"
  | "coding"
  | "research"
  | "finance"

export type AgentMode =
  | "single"
  | "team"

export type EliteStrategy =
  | "automatic"
  | "single_best"
  | "parallel_race"
  | "best_of_n"
  | "quality_weighted_fusion"
  | "expert_panel"
  | "challenge_and_refine"

// ============================================================
// Orchestration Models
// ============================================================

export interface TuningOptions {
  /** Enable prompt optimization */
  prompt_optimization?: boolean
  /** Enable output validation */
  output_validation?: boolean
  /** Enable structured answer formatting */
  answer_structure?: boolean
  /** Enable learning from conversation history */
  learn_from_chat?: boolean
}

export interface CriteriaSettings {
  /** Accuracy priority (0-100) */
  accuracy?: number
  /** Speed priority (0-100) */
  speed?: number
  /** Creativity priority (0-100) */
  creativity?: number
}

export interface ChatMetadata {
  /** Chat/conversation ID */
  chat_id: string | null
  /** User ID */
  user_id: string | null
  /** Project ID */
  project_id: string | null
  /** Dynamic criteria settings for quality/speed/creativity balance */
  criteria: CriteriaSettings | null
}

export interface OrchestrationSettings {
  /** Accuracy vs Speed slider (1=fastest, 5=most accurate) */
  accuracy_level?: number
  /** Enable Hierarchical Role Management (HRM) */
  enable_hrm?: boolean
  /** Enable Prompt Diffusion & Refinement */
  enable_prompt_diffusion?: boolean
  /** Enable Deep Consensus (multi-round debate) */
  enable_deep_consensus?: boolean
  /** Enable Adaptive Ensemble Logic */
  enable_adaptive_ensemble?: boolean
  /** Elite orchestration strategy */
  elite_strategy: string | null
  /** Quality boosting options */
  quality_options: Array<string> | null
  /** Temperature for response generation */
  temperature?: number | null
  /** Maximum tokens in response */
  max_tokens?: number | null
  /** Top-p nucleus sampling */
  top_p?: number | null
  /** Frequency penalty */
  frequency_penalty?: number | null
  /** Presence penalty */
  presence_penalty?: number | null
  /** Enable automatic tool detection and execution */
  enable_tool_broker?: boolean | null
  /** Enable code/math verification */
  enable_verification?: boolean | null
  /** Enable Vector RAG with Pinecone */
  enable_vector_rag?: boolean | null
  /** Enable memory augmentation */
  enable_memory?: boolean | null
}

export interface AgentTrace {
  /** Agent identifier */
  agent_id: string | null
  /** Agent name/type */
  agent_name: string | null
  /** Agent's contribution */
  contribution: string | null
  /** Confidence score */
  confidence: number | null
  /** Processing timestamp */
  timestamp: number | null
}

export interface ChatRequest {
  /** User prompt/question */
  prompt?: string
  /** List of model IDs to use for orchestration (e.g., ['gpt-5', 'claude-sonnet-4.5', 'grok-4']). If not provided, models will be auto-selected. */
  models: Array<string> | null
  /** Reasoning depth mode (fast/standard/deep) */
  reasoning_mode?: ReasoningMode
  /** Advanced reasoning method (chain-of-thought, tree-of-thought, react, plan-and-solve, self-consistency, reflexion). If not provided, will be inferred from reasoning_mode. */
  reasoning_method: ReasoningMethod | null
  /** Domain specialization pack */
  domain_pack?: DomainPack
  /** Agent collaboration mode */
  agent_mode?: AgentMode
  /** Tuning options */
  tuning?: TuningOptions
  /** Orchestration Studio settings */
  orchestration?: OrchestrationSettings
  /** Optional metadata */
  metadata?: ChatMetadata
  /** Conversation history as list of {role, content} dicts */
  history: Array<Record<string, unknown>> | null
}

export interface ChatResponse {
  /** Final assistant answer/message */
  message?: string
  /** List of models that participated in orchestration */
  models_used?: Array<string>
  /** Reasoning mode used */
  reasoning_mode?: ReasoningMode
  /** Advanced reasoning method used (if specified) */
  reasoning_method: ReasoningMethod | null
  /** Domain pack used */
  domain_pack?: DomainPack
  /** Agent mode used */
  agent_mode?: AgentMode
  /** Tuning options that were applied */
  used_tuning?: TuningOptions
  /** Metadata (echoed from request) */
  metadata?: ChatMetadata
  /** Total tokens consumed */
  tokens_used: number | null
  /** Processing latency in milliseconds */
  latency_ms: number | null
  /** Agent trace information */
  agent_traces?: Array<AgentTrace>
  /** Additional response data */
  extra?: Record<string, unknown>
}

// ============================================================
// Agent Models
// ============================================================

export interface AgentInfo {
  id?: string
  name?: string
  provider?: string
  available?: boolean
  description: string | null
  capabilities: Record<string, unknown> | null
}

export interface AgentsResponse {
  agents?: Array<AgentInfo>
  source?: string
}

// ============================================================
// Execute Models
// ============================================================

export interface ExecuteRequest {
  /** Code to execute */
  code?: string
  /** Programming language */
  language?: string
  /** Session token for sandbox isolation */
  session_token?: string
}

export interface ExecuteResponse {
  success?: boolean
  /** Execution output */
  output?: string
  /** Error message if execution failed */
  error: string | null
  /** Additional metadata */
  metadata?: Record<string, unknown>
}

// ============================================================
// Stub/Feature Models
// ============================================================

export interface FileAnalysisRequest {
  /** File identifier */
  file_id?: string
  /** Type of analysis to perform */
  analysis_type?: string
}

export interface FileAnalysisResponse {
  success?: boolean
  /** Analysis results */
  analysis?: Record<string, unknown>
  /** Status message */
  message?: string
}

export interface ImageGenerationRequest {
  /** Text prompt for image generation */
  prompt?: string
  /** Image style */
  style?: string
  /** Image dimensions */
  size?: string
}

export interface ImageGenerationResponse {
  success?: boolean
  /** URL of generated image */
  image_url: string | null
  /** Status message */
  message?: string
}

export interface DataVisualizationRequest {
  /** Data to visualize */
  data?: Record<string, unknown>
  /** Type of chart to generate */
  chart_type?: string
  /** Chart options */
  options?: Record<string, unknown>
}

export interface DataVisualizationResponse {
  success?: boolean
  /** URL of generated chart */
  chart_url: string | null
  /** Chart data structure */
  chart_data?: Record<string, unknown>
  /** Status message */
  message?: string
}

export interface CollaborationRequest {
  /** Collaboration action (share, invite, comment, etc.) */
  action?: string
  /** Resource identifier */
  resource_id?: string
  /** List of participant identifiers */
  participants?: Array<string>
  /** Additional metadata */
  metadata?: Record<string, unknown>
}

export interface CollaborationResponse {
  success?: boolean
  /** Collaboration result */
  result?: Record<string, unknown>
  /** Status message */
  message?: string
}

// ============================================================
// Reasoning Config Models
// ============================================================

export interface ReasoningConfigRequest {
  /** Reasoning mode: 'auto' or 'manual' */
  mode?: ReasoningMode
  /** List of selected reasoning methods (required for manual mode) */
  selectedMethods?: Array<string>
}

export interface ReasoningConfigResponse {
  mode?: string
  selectedMethods?: Array<string>
}

export interface ReasoningConfigSaveResponse {
  success?: boolean
  message?: string
  config?: ReasoningConfigResponse
}

// ============================================================
// Error Response
// ============================================================

export interface ErrorResponse {
  error: {
    code: string
    message: string
    details: Record<string, unknown>
    recoverable: boolean
  }
  correlation_id: string
  request_id: string | null
  timestamp: string
}
