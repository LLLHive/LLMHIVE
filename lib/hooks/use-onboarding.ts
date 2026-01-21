/**
 * Onboarding Hook - Manages first-time user experience
 * 
 * Tracks onboarding state via localStorage and provides
 * methods to control the onboarding flow.
 */
"use client"

import { useState, useEffect, useCallback } from "react"

const STORAGE_KEY = "llmhive-onboarding"

export interface OnboardingState {
  hasSeenWelcome: boolean
  hasCompletedTour: boolean
  currentStep: number
  dismissedAt?: string
  completedAt?: string
}

const DEFAULT_STATE: OnboardingState = {
  hasSeenWelcome: false,
  hasCompletedTour: false,
  currentStep: 0,
}

export interface UseOnboardingReturn {
  // State
  state: OnboardingState
  isLoading: boolean
  shouldShowWelcome: boolean
  shouldShowTour: boolean
  
  // Actions
  markWelcomeSeen: () => void
  startTour: () => void
  nextStep: () => void
  prevStep: () => void
  goToStep: (step: number) => void
  completeTour: () => void
  skipTour: () => void
  resetOnboarding: () => void
}

export function useOnboarding(): UseOnboardingReturn {
  const [state, setState] = useState<OnboardingState>(DEFAULT_STATE)
  const [isLoading, setIsLoading] = useState(true)

  // Load state from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored) as OnboardingState
        setState(parsed)
      }
    } catch (error) {
      console.error("[Onboarding] Failed to load state:", error)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Save state to localStorage
  const saveState = useCallback((newState: OnboardingState) => {
    setState(newState)
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newState))
    } catch (error) {
      console.error("[Onboarding] Failed to save state:", error)
    }
  }, [])

  // Mark welcome modal as seen
  const markWelcomeSeen = useCallback(() => {
    saveState({
      ...state,
      hasSeenWelcome: true,
    })
  }, [state, saveState])

  // Start the feature tour
  const startTour = useCallback(() => {
    saveState({
      ...state,
      hasSeenWelcome: true,
      currentStep: 1,
    })
  }, [state, saveState])

  // Navigate to next tour step
  const nextStep = useCallback(() => {
    saveState({
      ...state,
      currentStep: state.currentStep + 1,
    })
  }, [state, saveState])

  // Navigate to previous tour step
  const prevStep = useCallback(() => {
    saveState({
      ...state,
      currentStep: Math.max(0, state.currentStep - 1),
    })
  }, [state, saveState])

  // Go to specific step
  const goToStep = useCallback((step: number) => {
    saveState({
      ...state,
      currentStep: step,
    })
  }, [state, saveState])

  // Complete the tour
  const completeTour = useCallback(() => {
    saveState({
      ...state,
      hasCompletedTour: true,
      currentStep: 0,
      completedAt: new Date().toISOString(),
    })
  }, [state, saveState])

  // Skip the tour
  const skipTour = useCallback(() => {
    saveState({
      ...state,
      hasSeenWelcome: true,
      hasCompletedTour: true,
      currentStep: 0,
      dismissedAt: new Date().toISOString(),
    })
  }, [state, saveState])

  // Reset onboarding (for testing)
  const resetOnboarding = useCallback(() => {
    saveState(DEFAULT_STATE)
  }, [saveState])

  // Derived state
  const shouldShowWelcome = !isLoading && !state.hasSeenWelcome
  const shouldShowTour = !isLoading && state.hasSeenWelcome && !state.hasCompletedTour && state.currentStep > 0

  return {
    state,
    isLoading,
    shouldShowWelcome,
    shouldShowTour,
    markWelcomeSeen,
    startTour,
    nextStep,
    prevStep,
    goToStep,
    completeTour,
    skipTour,
    resetOnboarding,
  }
}
