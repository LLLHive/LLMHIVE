"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { useAuth } from "@/lib/auth-context"

export interface CollaborationUser {
  id: string
  name: string
  email: string
  avatar?: string
  role: "owner" | "editor" | "viewer"
  status: "online" | "offline" | "typing"
  cursor?: { x: number; y: number }
  lastSeen?: Date
}

export interface CollaborationMessage {
  id: string
  type: "chat" | "system" | "action"
  userId: string
  userName: string
  content: string
  timestamp: Date
}

export interface CollaborationState {
  sessionId: string | null
  users: CollaborationUser[]
  messages: CollaborationMessage[]
  isConnected: boolean
  isConnecting: boolean
  error: string | null
}

interface UseCollaborationOptions {
  sessionId?: string
  onUserJoin?: (user: CollaborationUser) => void
  onUserLeave?: (userId: string) => void
  onMessage?: (message: CollaborationMessage) => void
  onCursorMove?: (userId: string, cursor: { x: number; y: number }) => void
  onTypingStart?: (userId: string) => void
  onTypingStop?: (userId: string) => void
}

const WS_RECONNECT_DELAY = 3000
const WS_MAX_RETRIES = 5

/**
 * Hook for real-time collaboration via WebSocket
 */
export function useCollaboration(options: UseCollaborationOptions = {}) {
  const auth = useAuth()
  const [state, setState] = useState<CollaborationState>({
    sessionId: options.sessionId || null,
    users: [],
    messages: [],
    isConnected: false,
    isConnecting: false,
    error: null,
  })

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)

  // Get WebSocket URL
  const getWsUrl = useCallback(() => {
    const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
    const wsProtocol = backendUrl.startsWith("https") ? "wss" : "ws"
    const wsHost = backendUrl.replace(/^https?:\/\//, "")
    return `${wsProtocol}://${wsHost}/ws/collaborate/${state.sessionId}`
  }, [state.sessionId])

  // Send message through WebSocket
  const sendWsMessage = useCallback((type: string, payload: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, ...payload }))
    }
  }, [])

  // Connect to WebSocket
  const connect = useCallback(async (sessionId: string) => {
    if (!auth?.user?.id) {
      setState(prev => ({ ...prev, error: "Authentication required" }))
      return
    }

    setState(prev => ({ ...prev, sessionId, isConnecting: true, error: null }))

    try {
      const wsUrl = `${getWsUrl()}?userId=${auth.user.id}&userName=${encodeURIComponent(auth.user.email || "User")}`
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log("[Collaboration] WebSocket connected")
        reconnectAttemptsRef.current = 0
        setState(prev => ({ ...prev, isConnected: true, isConnecting: false }))
        
        // Send join message
        sendWsMessage("join", {
          userId: auth.user?.id,
          userName: auth.user?.email,
        })
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          handleWsMessage(data)
        } catch (e) {
          console.error("[Collaboration] Failed to parse message:", e)
        }
      }

      ws.onerror = (error) => {
        console.error("[Collaboration] WebSocket error:", error)
        setState(prev => ({ ...prev, error: "Connection error" }))
      }

      ws.onclose = (event) => {
        console.log("[Collaboration] WebSocket closed:", event.code, event.reason)
        setState(prev => ({ ...prev, isConnected: false }))
        wsRef.current = null

        // Attempt reconnection
        if (reconnectAttemptsRef.current < WS_MAX_RETRIES) {
          reconnectAttemptsRef.current++
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log(`[Collaboration] Reconnecting (attempt ${reconnectAttemptsRef.current})...`)
            connect(sessionId)
          }, WS_RECONNECT_DELAY)
        }
      }

      wsRef.current = ws
    } catch (e) {
      console.error("[Collaboration] Failed to connect:", e)
      setState(prev => ({ ...prev, isConnecting: false, error: "Failed to connect" }))
    }
  }, [auth?.user?.id, auth?.user?.email, getWsUrl, sendWsMessage])

  // Handle incoming WebSocket messages
  const handleWsMessage = useCallback((data: any) => {
    switch (data.type) {
      case "user_join":
        const newUser: CollaborationUser = {
          id: data.userId,
          name: data.userName,
          email: data.userEmail || "",
          role: data.role || "viewer",
          status: "online",
          lastSeen: new Date(),
        }
        setState(prev => ({
          ...prev,
          users: [...prev.users.filter(u => u.id !== newUser.id), newUser],
        }))
        options.onUserJoin?.(newUser)
        break

      case "user_leave":
        setState(prev => ({
          ...prev,
          users: prev.users.filter(u => u.id !== data.userId),
        }))
        options.onUserLeave?.(data.userId)
        break

      case "users_list":
        const users: CollaborationUser[] = (data.users || []).map((u: any) => ({
          id: u.userId,
          name: u.userName,
          email: u.userEmail || "",
          role: u.role || "viewer",
          status: u.status || "online",
          lastSeen: new Date(),
        }))
        setState(prev => ({ ...prev, users }))
        break

      case "chat":
        const message: CollaborationMessage = {
          id: data.messageId || `msg-${Date.now()}`,
          type: "chat",
          userId: data.userId,
          userName: data.userName,
          content: data.content,
          timestamp: new Date(data.timestamp || Date.now()),
        }
        setState(prev => ({
          ...prev,
          messages: [...prev.messages, message],
        }))
        options.onMessage?.(message)
        break

      case "cursor_move":
        options.onCursorMove?.(data.userId, data.cursor)
        setState(prev => ({
          ...prev,
          users: prev.users.map(u =>
            u.id === data.userId ? { ...u, cursor: data.cursor } : u
          ),
        }))
        break

      case "typing_start":
        options.onTypingStart?.(data.userId)
        setState(prev => ({
          ...prev,
          users: prev.users.map(u =>
            u.id === data.userId ? { ...u, status: "typing" } : u
          ),
        }))
        break

      case "typing_stop":
        options.onTypingStop?.(data.userId)
        setState(prev => ({
          ...prev,
          users: prev.users.map(u =>
            u.id === data.userId ? { ...u, status: "online" } : u
          ),
        }))
        break

      case "error":
        console.error("[Collaboration] Server error:", data.message)
        setState(prev => ({ ...prev, error: data.message }))
        break

      default:
        console.log("[Collaboration] Unknown message type:", data.type)
    }
  }, [options])

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
    setState(prev => ({
      ...prev,
      isConnected: false,
      isConnecting: false,
      sessionId: null,
      users: [],
      messages: [],
    }))
  }, [])

  // Send chat message
  const sendMessage = useCallback((content: string) => {
    if (!state.isConnected || !auth?.user?.id) return

    sendWsMessage("chat", {
      userId: auth.user.id,
      userName: auth.user.email,
      content,
      timestamp: new Date().toISOString(),
    })
  }, [state.isConnected, auth?.user?.id, auth?.user?.email, sendWsMessage])

  // Send cursor position
  const sendCursorMove = useCallback((x: number, y: number) => {
    if (!state.isConnected || !auth?.user?.id) return

    sendWsMessage("cursor_move", {
      userId: auth.user.id,
      cursor: { x, y },
    })
  }, [state.isConnected, auth?.user?.id, sendWsMessage])

  // Send typing indicator
  const sendTypingStart = useCallback(() => {
    if (!state.isConnected || !auth?.user?.id) return
    sendWsMessage("typing_start", { userId: auth.user.id })
  }, [state.isConnected, auth?.user?.id, sendWsMessage])

  const sendTypingStop = useCallback(() => {
    if (!state.isConnected || !auth?.user?.id) return
    sendWsMessage("typing_stop", { userId: auth.user.id })
  }, [state.isConnected, auth?.user?.id, sendWsMessage])

  // Create new session
  const createSession = useCallback(async (): Promise<string | null> => {
    if (!auth?.user?.id) return null

    try {
      const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"
      const response = await fetch(`${backendUrl}/api/v1/collaborate/sessions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-Id": auth.user.id,
        },
        body: JSON.stringify({
          name: "New Session",
          createdBy: auth.user.id,
        }),
      })

      if (!response.ok) {
        throw new Error("Failed to create session")
      }

      const data = await response.json()
      return data.sessionId
    } catch (e) {
      console.error("[Collaboration] Failed to create session:", e)
      setState(prev => ({ ...prev, error: "Failed to create session" }))
      return null
    }
  }, [auth?.user?.id])

  // Clean up on unmount
  useEffect(() => {
    return () => {
      disconnect()
    }
  }, [disconnect])

  return {
    ...state,
    connect,
    disconnect,
    sendMessage,
    sendCursorMove,
    sendTypingStart,
    sendTypingStop,
    createSession,
  }
}

