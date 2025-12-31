"use client"

import { useState, useEffect, useCallback } from "react"
import { useAuth } from "@/lib/auth-context"
import type { Conversation, Project } from "@/lib/types"

const CONVERSATIONS_KEY = "llmhive-conversations"
const PROJECTS_KEY = "llmhive-projects"

interface UseConversationsReturn {
  conversations: Conversation[]
  projects: Project[]
  isLoading: boolean
  error: string | null
  // Conversation actions
  createConversation: (conv: Conversation) => Promise<void>
  updateConversation: (id: string, updates: Partial<Conversation>) => Promise<void>
  deleteConversation: (id: string) => Promise<void>
  // Project actions
  createProject: (project: Project) => Promise<void>
  updateProject: (id: string, updates: Partial<Project>) => Promise<void>
  deleteProject: (id: string) => Promise<void>
  addConversationToProject: (conversationId: string, projectId: string) => Promise<void>
  removeConversationFromProject: (conversationId: string, projectId: string) => Promise<void>
  // Sync
  syncNow: () => Promise<void>
}

/**
 * Hook for managing conversations and projects with persistent storage
 * 
 * - For authenticated users: Syncs to server API + localStorage cache
 * - For unauthenticated users: localStorage only
 * - Automatically syncs on changes
 */
export function useConversations(): UseConversationsReturn {
  const auth = useAuth()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isInitialized, setIsInitialized] = useState(false)

  // Load data on mount
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      setError(null)

      try {
        // Try to load from API first (if authenticated)
        if (auth?.isAuthenticated && auth?.user?.id) {
          try {
            const [convRes, projRes] = await Promise.all([
              fetch("/api/conversations"),
              fetch("/api/projects"),
            ])

            if (convRes.ok && projRes.ok) {
              const convData = await convRes.json()
              const projData = await projRes.json()
              
              // Restore Date objects
              const restoredConvs = (convData.conversations || []).map((c: any) => ({
                ...c,
                createdAt: new Date(c.createdAt),
                updatedAt: new Date(c.updatedAt),
                messages: (c.messages || []).map((m: any) => ({
                  ...m,
                  timestamp: new Date(m.timestamp),
                })),
              }))
              
              const restoredProjects = (projData.projects || []).map((p: any) => ({
                ...p,
                createdAt: new Date(p.createdAt),
              }))

              setConversations(restoredConvs)
              setProjects(restoredProjects)
              
              // Also cache to localStorage
              localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(restoredConvs))
              localStorage.setItem(PROJECTS_KEY, JSON.stringify(restoredProjects))
              
              console.log(`[useConversations] Loaded from API: ${restoredConvs.length} conversations, ${restoredProjects.length} projects`)
              setIsInitialized(true)
              setIsLoading(false)
              return
            }
          } catch (apiError) {
            console.warn("[useConversations] API load failed, falling back to localStorage:", apiError)
          }
        }

        // Fallback to localStorage
        const savedConversations = localStorage.getItem(CONVERSATIONS_KEY)
        const savedProjects = localStorage.getItem(PROJECTS_KEY)

        if (savedConversations) {
          const parsed = JSON.parse(savedConversations)
          const restored = parsed.map((c: any) => ({
            ...c,
            createdAt: new Date(c.createdAt),
            updatedAt: new Date(c.updatedAt),
            messages: (c.messages || []).map((m: any) => ({
              ...m,
              timestamp: new Date(m.timestamp),
            })),
          }))
          setConversations(restored)
        }

        if (savedProjects) {
          const parsed = JSON.parse(savedProjects)
          const restored = parsed.map((p: any) => ({
            ...p,
            createdAt: new Date(p.createdAt),
          }))
          setProjects(restored)
        }

        console.log("[useConversations] Loaded from localStorage")
        setIsInitialized(true)
      } catch (e) {
        console.error("[useConversations] Failed to load:", e)
        setError("Failed to load data")
      } finally {
        setIsLoading(false)
      }
    }

    loadData()
  }, [auth?.isAuthenticated, auth?.user?.id])

  // Save to localStorage when data changes
  useEffect(() => {
    if (!isInitialized) return
    
    try {
      localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(conversations))
    } catch (e) {
      console.error("[useConversations] Failed to save conversations to localStorage:", e)
    }
  }, [conversations, isInitialized])

  useEffect(() => {
    if (!isInitialized) return
    
    try {
      localStorage.setItem(PROJECTS_KEY, JSON.stringify(projects))
    } catch (e) {
      console.error("[useConversations] Failed to save projects to localStorage:", e)
    }
  }, [projects, isInitialized])

  // Sync to API when data changes (debounced)
  useEffect(() => {
    if (!isInitialized || !auth?.isAuthenticated) return

    const syncToApi = async () => {
      try {
        await Promise.all([
          fetch("/api/conversations", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "sync", conversations }),
          }),
          fetch("/api/projects", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: "sync", projects }),
          }),
        ])
        console.log("[useConversations] Synced to API")
      } catch (e) {
        console.error("[useConversations] API sync failed:", e)
      }
    }

    // Debounce sync to avoid too many requests
    const timeoutId = setTimeout(syncToApi, 1000)
    return () => clearTimeout(timeoutId)
  }, [conversations, projects, isInitialized, auth?.isAuthenticated])

  // Conversation actions
  const createConversation = useCallback(async (conv: Conversation) => {
    setConversations(prev => [conv, ...prev])
  }, [])

  const updateConversation = useCallback(async (id: string, updates: Partial<Conversation>) => {
    setConversations(prev =>
      prev.map(c => (c.id === id ? { ...c, ...updates, updatedAt: new Date() } : c))
    )
  }, [])

  const deleteConversation = useCallback(async (id: string) => {
    setConversations(prev => prev.filter(c => c.id !== id))
    // Also remove from all projects
    setProjects(prev =>
      prev.map(p => ({
        ...p,
        conversations: p.conversations.filter(cid => cid !== id),
      }))
    )
  }, [])

  // Project actions
  const createProject = useCallback(async (project: Project) => {
    setProjects(prev => [...prev, project])
  }, [])

  const updateProject = useCallback(async (id: string, updates: Partial<Project>) => {
    setProjects(prev =>
      prev.map(p => (p.id === id ? { ...p, ...updates } : p))
    )
  }, [])

  const deleteProject = useCallback(async (id: string) => {
    setProjects(prev => prev.filter(p => p.id !== id))
  }, [])

  const addConversationToProject = useCallback(async (conversationId: string, projectId: string) => {
    setProjects(prev =>
      prev.map(p => {
        if (p.id === projectId) {
          const convs = p.conversations || []
          if (!convs.includes(conversationId)) {
            return { ...p, conversations: [...convs, conversationId] }
          }
        }
        return p
      })
    )
  }, [])

  const removeConversationFromProject = useCallback(async (conversationId: string, projectId: string) => {
    setProjects(prev =>
      prev.map(p => {
        if (p.id === projectId) {
          return { ...p, conversations: (p.conversations || []).filter(id => id !== conversationId) }
        }
        return p
      })
    )
  }, [])

  const syncNow = useCallback(async () => {
    if (!auth?.isAuthenticated) return
    
    try {
      await Promise.all([
        fetch("/api/conversations", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "sync", conversations }),
        }),
        fetch("/api/projects", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "sync", projects }),
        }),
      ])
      console.log("[useConversations] Manual sync completed")
    } catch (e) {
      console.error("[useConversations] Manual sync failed:", e)
      throw e
    }
  }, [auth?.isAuthenticated, conversations, projects])

  return {
    conversations,
    projects,
    isLoading,
    error,
    createConversation,
    updateConversation,
    deleteConversation,
    createProject,
    updateProject,
    deleteProject,
    addConversationToProject,
    removeConversationFromProject,
    syncNow,
  }
}

