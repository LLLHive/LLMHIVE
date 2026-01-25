"use client"

import { createContext, useContext, ReactNode, useState, useEffect, useCallback, useRef } from "react"
import { useAuth } from "@/lib/auth-context"
import type { Conversation, Project } from "@/lib/types"

const CONVERSATIONS_KEY = "llmhive-conversations"
const PROJECTS_KEY = "llmhive-projects"
const SYNC_DEBOUNCE_MS = 2000
const MAX_SYNC_RETRIES = 3
const SYNC_RETRY_DELAY_MS = 1000

interface ConversationsContextValue {
  conversations: Conversation[]
  projects: Project[]
  currentConversation: Conversation | null
  isLoading: boolean
  isSyncing: boolean
  error: string | null
  lastSyncedAt: Date | null
  // Current conversation
  setCurrentConversation: (conv: Conversation | null) => void
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

const ConversationsContext = createContext<ConversationsContextValue | null>(null)

/**
 * Hook to access shared conversations state
 * Must be used within ConversationsProvider
 */
export function useConversationsContext(): ConversationsContextValue {
  const context = useContext(ConversationsContext)
  if (!context) {
    throw new Error("useConversationsContext must be used within ConversationsProvider")
  }
  return context
}

// Alias for backwards compatibility and convenience
export const useConversations = useConversationsContext

/**
 * Provider that shares conversation state across the entire app
 * Uses localStorage for immediate persistence + API sync for cross-device/browser
 */
export function ConversationsProvider({ children }: { children: ReactNode }) {
  const auth = useAuth()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSyncing, setIsSyncing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isInitialized, setIsInitialized] = useState(false)
  const [lastSyncedAt, setLastSyncedAt] = useState<Date | null>(null)
  
  // Ref to track pending changes for smart sync
  const pendingChangesRef = useRef<{ conversations: boolean; projects: boolean }>({
    conversations: false,
    projects: false,
  })

  // Load data on mount - localStorage first, then merge with API
  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      setError(null)

      // ALWAYS load localStorage first as the source of truth
      let localConvs: Conversation[] = []
      let localProjects: Project[] = []
      
      try {
        const savedConversations = localStorage.getItem(CONVERSATIONS_KEY)
        const savedProjects = localStorage.getItem(PROJECTS_KEY)

        if (savedConversations) {
          const parsed = JSON.parse(savedConversations)
          localConvs = parsed.map((c: any) => ({
            ...c,
            createdAt: new Date(c.createdAt),
            updatedAt: new Date(c.updatedAt),
            messages: (c.messages || []).map((m: any) => ({
              ...m,
              timestamp: new Date(m.timestamp),
            })),
          }))
        }

        if (savedProjects) {
          const parsed = JSON.parse(savedProjects)
          localProjects = parsed.map((p: any) => ({
            ...p,
            createdAt: new Date(p.createdAt),
          }))
        }
        
        console.log(`[ConversationsContext] Loaded from localStorage: ${localConvs.length} conversations, ${localProjects.length} projects`)
      } catch (e) {
        console.error("[ConversationsContext] Failed to load from localStorage:", e)
      }

      // Set localStorage data immediately so user sees their data
      setConversations(localConvs)
      setProjects(localProjects)

      try {
        // Try to load from API (if authenticated) and merge with localStorage
        if (auth?.isAuthenticated && auth?.user?.id) {
          try {
            // Use retry logic for resilient API calls
            const [convRes, projRes] = await Promise.all([
              fetchWithRetry("/api/conversations", { method: "GET" }),
              fetchWithRetry("/api/projects", { method: "GET" }),
            ])

            if (convRes.ok && projRes.ok) {
              const convData = await convRes.json()
              const projData = await projRes.json()
              
              // Restore Date objects
              const apiConvs = (convData.conversations || []).map((c: any) => ({
                ...c,
                createdAt: new Date(c.createdAt),
                updatedAt: new Date(c.updatedAt),
                messages: (c.messages || []).map((m: any) => ({
                  ...m,
                  timestamp: new Date(m.timestamp),
                })),
              }))
              
              const apiProjects = (projData.projects || []).map((p: any) => ({
                ...p,
                createdAt: new Date(p.createdAt),
              }))

              console.log(`[ConversationsContext] API returned: ${apiConvs.length} conversations, ${apiProjects.length} projects (storage: ${convData.storage})`)
              
              // Merge strategy: Combine local and remote, keeping the most recent version of each
              const mergedConvs = mergeByTimestamp(localConvs, apiConvs)
              const mergedProjects = mergeByTimestamp(localProjects, apiProjects)
              
              // Update state and localStorage with merged data
              setConversations(mergedConvs)
              localStorage.setItem(CONVERSATIONS_KEY, JSON.stringify(mergedConvs))
              console.log(`[ConversationsContext] Merged conversations: ${mergedConvs.length} total (local: ${localConvs.length}, remote: ${apiConvs.length})`)
              
              setProjects(mergedProjects)
              localStorage.setItem(PROJECTS_KEY, JSON.stringify(mergedProjects))
              console.log(`[ConversationsContext] Merged projects: ${mergedProjects.length} total`)
              
              // Immediately sync merged data back to API to ensure consistency
              if (mergedConvs.length > apiConvs.length || mergedProjects.length > apiProjects.length) {
                console.log("[ConversationsContext] Local has more data, syncing to API...")
                pendingChangesRef.current = { conversations: true, projects: true }
              }
              
              setLastSyncedAt(new Date())
              setIsInitialized(true)
              setIsLoading(false)
              return
            } else {
              console.warn(`[ConversationsContext] API returned non-OK: convRes=${convRes.status}, projRes=${projRes.status}`)
            }
          } catch (apiError) {
            console.warn("[ConversationsContext] API load failed after retries, using localStorage:", apiError)
          }
        }

        // Already loaded from localStorage above - just mark as initialized
        console.log("[ConversationsContext] Using localStorage data (no API or unauthenticated)")
        setIsInitialized(true)
      } catch (e) {
        console.error("[ConversationsContext] Failed to load:", e)
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
      pendingChangesRef.current.conversations = true
    } catch (e) {
      console.error("[ConversationsContext] Failed to save conversations to localStorage:", e)
    }
  }, [conversations, isInitialized])

  useEffect(() => {
    if (!isInitialized) return
    
    try {
      localStorage.setItem(PROJECTS_KEY, JSON.stringify(projects))
      pendingChangesRef.current.projects = true
    } catch (e) {
      console.error("[ConversationsContext] Failed to save projects to localStorage:", e)
    }
  }, [projects, isInitialized])

  // Debounced sync to API when data changes - with retry logic
  useEffect(() => {
    if (!isInitialized || !auth?.isAuthenticated) return

    const syncToApi = async () => {
      if (!pendingChangesRef.current.conversations && !pendingChangesRef.current.projects) {
        return // No changes to sync
      }

      setIsSyncing(true)
      
      try {
        const promises: Promise<Response>[] = []
        
        if (pendingChangesRef.current.conversations) {
          promises.push(
            fetchWithRetry("/api/conversations", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ 
                action: "sync", 
                conversations: conversations.map(c => ({
                  ...c,
                  createdAt: c.createdAt.toISOString(),
                  updatedAt: c.updatedAt.toISOString(),
                  messages: c.messages.map(m => ({
                    ...m,
                    timestamp: m.timestamp.toISOString(),
                  })),
                })),
              }),
            })
          )
        }
        
        if (pendingChangesRef.current.projects) {
          promises.push(
            fetchWithRetry("/api/projects", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ 
                action: "sync", 
                projects: projects.map(p => ({
                  ...p,
                  createdAt: p.createdAt.toISOString(),
                })),
              }),
            })
          )
        }
        
        const results = await Promise.all(promises)
        
        // Check if all syncs succeeded
        const allSucceeded = results.every(r => r.ok)
        
        if (allSucceeded) {
          // Clear pending changes only if sync succeeded
          pendingChangesRef.current = { conversations: false, projects: false }
          setLastSyncedAt(new Date())
          console.log("[ConversationsContext] ✅ Synced to API successfully")
        } else {
          console.warn("[ConversationsContext] ⚠️ Some syncs failed, will retry on next change")
        }
      } catch (e) {
        console.error("[ConversationsContext] ❌ API sync failed after retries:", e)
        // Don't clear pending changes - will retry on next change
      } finally {
        setIsSyncing(false)
      }
    }

    // Debounce sync to avoid too many requests
    const timeoutId = setTimeout(syncToApi, SYNC_DEBOUNCE_MS)
    return () => clearTimeout(timeoutId)
  }, [conversations, projects, isInitialized, auth?.isAuthenticated])

  // Conversation actions
  const createConversation = useCallback(async (conv: Conversation) => {
    setConversations(prev => [conv, ...prev])
    setCurrentConversation(conv)
  }, [])

  const updateConversation = useCallback(async (id: string, updates: Partial<Conversation>) => {
    setConversations(prev =>
      prev.map(c => (c.id === id ? { ...c, ...updates, updatedAt: new Date() } : c))
    )
    // Also update current if it's the active one
    setCurrentConversation(prev => 
      prev?.id === id ? { ...prev, ...updates, updatedAt: new Date() } : prev
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
    // Clear current if deleted
    setCurrentConversation(prev => prev?.id === id ? null : prev)
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
    // Also update conversation's projectId
    setConversations(prev =>
      prev.map(c => (c.id === conversationId ? { ...c, projectId, updatedAt: new Date() } : c))
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
    // Also update conversation's projectId
    setConversations(prev =>
      prev.map(c => (c.id === conversationId && c.projectId === projectId ? { ...c, projectId: undefined, updatedAt: new Date() } : c))
    )
  }, [])

  const syncNow = useCallback(async () => {
    if (!auth?.isAuthenticated) return
    
    setIsSyncing(true)
    
    try {
      const results = await Promise.all([
        fetchWithRetry("/api/conversations", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            action: "sync", 
            conversations: conversations.map(c => ({
              ...c,
              createdAt: c.createdAt.toISOString(),
              updatedAt: c.updatedAt.toISOString(),
              messages: c.messages.map(m => ({
                ...m,
                timestamp: m.timestamp.toISOString(),
              })),
            })),
          }),
        }),
        fetchWithRetry("/api/projects", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            action: "sync", 
            projects: projects.map(p => ({
              ...p,
              createdAt: p.createdAt.toISOString(),
            })),
          }),
        }),
      ])
      
      const allSucceeded = results.every(r => r.ok)
      
      if (allSucceeded) {
        pendingChangesRef.current = { conversations: false, projects: false }
        setLastSyncedAt(new Date())
        console.log("[ConversationsContext] ✅ Manual sync completed successfully")
      } else {
        throw new Error("Some syncs failed")
      }
    } catch (e) {
      console.error("[ConversationsContext] ❌ Manual sync failed:", e)
      throw e
    } finally {
      setIsSyncing(false)
    }
  }, [auth?.isAuthenticated, conversations, projects])

  const value: ConversationsContextValue = {
    conversations,
    projects,
    currentConversation,
    isLoading,
    isSyncing,
    error,
    lastSyncedAt,
    setCurrentConversation,
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

  return (
    <ConversationsContext.Provider value={value}>
      {children}
    </ConversationsContext.Provider>
  )
}

/**
 * Fetch with retry logic for resilient API calls
 */
async function fetchWithRetry(
  url: string,
  options: RequestInit,
  maxRetries: number = MAX_SYNC_RETRIES
): Promise<Response> {
  let lastError: Error | null = null
  
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const response = await fetch(url, options)
      
      // Success or client error (don't retry 4xx)
      if (response.ok || (response.status >= 400 && response.status < 500)) {
        return response
      }
      
      // Server error (5xx) - retry
      console.warn(`[ConversationsContext] API ${url} returned ${response.status}, retry ${attempt + 1}/${maxRetries}`)
      lastError = new Error(`HTTP ${response.status}`)
      
    } catch (error) {
      // Network error - retry
      console.warn(`[ConversationsContext] Network error for ${url}, retry ${attempt + 1}/${maxRetries}:`, error)
      lastError = error as Error
    }
    
    // Wait before retry with exponential backoff
    if (attempt < maxRetries - 1) {
      await new Promise(resolve => setTimeout(resolve, SYNC_RETRY_DELAY_MS * Math.pow(2, attempt)))
    }
  }
  
  throw lastError || new Error("Max retries exceeded")
}

/**
 * Merge two arrays of items by ID, preferring the more recently updated item
 */
function mergeByTimestamp<T extends { id: string; updatedAt?: Date }>(
  local: T[],
  remote: T[]
): T[] {
  const map = new Map<string, T>()
  
  // Add all local items
  for (const item of local) {
    map.set(item.id, item)
  }
  
  // Merge remote items - prefer more recent
  for (const item of remote) {
    const existing = map.get(item.id)
    if (!existing) {
      map.set(item.id, item)
    } else if (item.updatedAt && existing.updatedAt) {
      const itemTime = new Date(item.updatedAt).getTime()
      const existingTime = new Date(existing.updatedAt).getTime()
      if (itemTime > existingTime) {
        map.set(item.id, item)
      }
    }
  }
  
  // Sort by updatedAt descending
  return Array.from(map.values()).sort((a, b) => {
    const aTime = a.updatedAt ? new Date(a.updatedAt).getTime() : 0
    const bTime = b.updatedAt ? new Date(b.updatedAt).getTime() : 0
    return bTime - aTime
  })
}
