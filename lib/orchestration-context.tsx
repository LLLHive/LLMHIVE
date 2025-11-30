"use client"

import React, { createContext, useContext, useState, useCallback, useRef } from "react"
import type { OrchestrationStatus, OrchestrationEvent, OrchestrationEventType } from "./types"

interface OrchestrationContextValue {
  status: OrchestrationStatus
  startOrchestration: () => void
  addEvent: (type: OrchestrationEventType, message: string, modelName?: string, details?: string) => void
  completeOrchestration: (modelsUsed: string[], tokens?: number, latencyMs?: number) => void
  resetOrchestration: () => void
  setModelsUsed: (models: string[]) => void
}

const initialStatus: OrchestrationStatus = {
  isActive: false,
  currentStep: "",
  events: [],
  modelsUsed: [],
}

const OrchestrationContext = createContext<OrchestrationContextValue | null>(null)

export function OrchestrationProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<OrchestrationStatus>(initialStatus)
  const eventIdRef = useRef(0)

  const startOrchestration = useCallback(() => {
    setStatus({
      isActive: true,
      currentStep: "Starting orchestration...",
      events: [
        {
          id: `evt-${++eventIdRef.current}`,
          type: "started",
          message: "Orchestration initiated",
          timestamp: new Date(),
          progress: 0,
        },
      ],
      modelsUsed: [],
      startTime: new Date(),
    })
  }, [])

  const addEvent = useCallback(
    (type: OrchestrationEventType, message: string, modelName?: string, details?: string) => {
      const newEvent: OrchestrationEvent = {
        id: `evt-${++eventIdRef.current}`,
        type,
        message,
        timestamp: new Date(),
        modelName,
        details,
        progress: getProgressForEventType(type),
      }

      setStatus((prev) => ({
        ...prev,
        currentStep: message,
        events: [...prev.events, newEvent],
      }))
    },
    []
  )

  const completeOrchestration = useCallback(
    (modelsUsed: string[], tokens?: number, latencyMs?: number) => {
      setStatus((prev) => ({
        ...prev,
        isActive: false,
        currentStep: "Completed",
        modelsUsed,
        endTime: new Date(),
        totalTokens: tokens,
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
    },
    []
  )

  const resetOrchestration = useCallback(() => {
    setStatus(initialStatus)
  }, [])

  const setModelsUsed = useCallback((models: string[]) => {
    setStatus((prev) => ({ ...prev, modelsUsed: models }))
  }, [])

  return (
    <OrchestrationContext.Provider
      value={{
        status,
        startOrchestration,
        addEvent,
        completeOrchestration,
        resetOrchestration,
        setModelsUsed,
      }}
    >
      {children}
    </OrchestrationContext.Provider>
  )
}

export function useOrchestration() {
  const context = useContext(OrchestrationContext)
  if (!context) {
    throw new Error("useOrchestration must be used within an OrchestrationProvider")
  }
  return context
}

function getProgressForEventType(type: OrchestrationEventType): number {
  const progressMap: Record<OrchestrationEventType, number> = {
    started: 5,
    refining_prompt: 15,
    dispatching_model: 25,
    model_responding: 45,
    model_critiquing: 60,
    verifying_facts: 75,
    consensus_building: 85,
    finalizing: 95,
    completed: 100,
    error: 0,
  }
  return progressMap[type] ?? 50
}

