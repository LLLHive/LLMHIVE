/**
 * Settings Storage - Persist orchestrator settings across pages
 * 
 * This module handles saving and loading orchestrator settings to/from
 * localStorage so they persist when navigating between pages.
 */

import type { OrchestratorSettings } from "./types"

const STORAGE_KEY = "llmhive-orchestrator-settings"

// Default settings - aligned with backend capabilities
export const DEFAULT_ORCHESTRATOR_SETTINGS: OrchestratorSettings = {
  reasoningMode: "standard",
  domainPack: "default",
  agentMode: "team",
  promptOptimization: true,
  outputValidation: true,
  answerStructure: true,
  sharedMemory: false,
  learnFromChat: false,
  selectedModels: ["automatic"],
  advancedReasoningMethods: ["automatic"],
  advancedFeatures: [],
  accuracyLevel: 3,
  enableHRM: false,
  enablePromptDiffusion: false,
  enableDeepConsensus: false,
  enableAdaptiveEnsemble: false,
  criteria: {
    accuracy: 70,
    speed: 70,
    creativity: 50,
  },
  // Elite Orchestration settings (default to automatic/on)
  eliteStrategy: "automatic", // Let system choose strategy
  qualityOptions: ["verification", "consensus"], // Default quality techniques
  enableToolBroker: true, // Enable automatic tool detection
  enableVerification: true, // Enable code/math verification
  enablePromptOps: true, // Always-on prompt preprocessing
  enableAnswerRefiner: true, // Always-on answer polishing
  // Standard LLM parameters
  standardValues: {
    temperature: 0.7,
    maxTokens: 2000,
    topP: 0.9,
    frequencyPenalty: 0,
    presencePenalty: 0,
  },
}

/**
 * Save orchestrator settings to localStorage
 */
export function saveOrchestratorSettings(settings: Partial<OrchestratorSettings>): void {
  if (typeof window === "undefined") return
  
  try {
    // Get existing settings and merge with new ones
    const existing = loadOrchestratorSettings()
    const merged = { ...existing, ...settings }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(merged))
  } catch (error) {
    console.error("Failed to save orchestrator settings:", error)
  }
}

/**
 * Load orchestrator settings from localStorage
 */
export function loadOrchestratorSettings(): OrchestratorSettings {
  if (typeof window === "undefined") return DEFAULT_ORCHESTRATOR_SETTINGS
  
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (!stored) return DEFAULT_ORCHESTRATOR_SETTINGS
    
    const parsed = JSON.parse(stored)
    // Merge with defaults to ensure all fields exist
    return { ...DEFAULT_ORCHESTRATOR_SETTINGS, ...parsed }
  } catch (error) {
    console.error("Failed to load orchestrator settings:", error)
    return DEFAULT_ORCHESTRATOR_SETTINGS
  }
}

/**
 * Clear all orchestrator settings
 */
export function clearOrchestratorSettings(): void {
  if (typeof window === "undefined") return
  
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch (error) {
    console.error("Failed to clear orchestrator settings:", error)
  }
}

/**
 * Check if settings have been customized from defaults
 */
export function hasCustomSettings(): boolean {
  if (typeof window === "undefined") return false
  
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored !== null
  } catch {
    return false
  }
}

