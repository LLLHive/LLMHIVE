"use client"

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { toast } from './toast'

// User type
export interface User {
  id: string
  name: string
  email: string
  image?: string
  provider?: 'github' | 'google' | 'email'
}

// Auth context type
interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  signIn: (provider: 'github' | 'google') => Promise<void>
  signOut: () => Promise<void>
  updateProfile: (updates: Partial<User>) => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

// Storage key for user data
const USER_STORAGE_KEY = 'llmhive-user'

// GitHub OAuth configuration
const GITHUB_CLIENT_ID = process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID || ''
const GOOGLE_CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID || ''

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Load user from storage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(USER_STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        setUser(parsed)
      }
    } catch (error) {
      console.error('Failed to load user from storage:', error)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Handle OAuth callback (check URL params)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    const provider = params.get('provider') || localStorage.getItem('llmhive-auth-provider')
    
    if (code && provider) {
      handleOAuthCallback(code, provider as 'github' | 'google')
    }
  }, [])

  const handleOAuthCallback = async (code: string, provider: 'github' | 'google') => {
    try {
      setIsLoading(true)
      
      // In production, this would exchange the code for tokens via your backend
      // For now, we'll simulate a successful login
      
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname)
      localStorage.removeItem('llmhive-auth-provider')
      
      // Simulate fetching user data (in production, call your auth API)
      const mockUser: User = {
        id: `user-${Date.now()}`,
        name: 'Demo User',
        email: 'user@example.com',
        provider,
        image: `https://api.dicebear.com/7.x/avataaars/svg?seed=${Date.now()}`,
      }
      
      setUser(mockUser)
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(mockUser))
      toast.success('Welcome! Signed in successfully.')
    } catch (error) {
      console.error('OAuth callback error:', error)
      toast.error('Sign in failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const signIn = useCallback(async (provider: 'github' | 'google') => {
    try {
      // Store provider for callback
      localStorage.setItem('llmhive-auth-provider', provider)
      
      if (provider === 'github') {
        if (!GITHUB_CLIENT_ID) {
          // Demo mode - create mock user
          toast.info("Demo Mode: GitHub OAuth not configured. Using demo account.")
          const demoUser: User = {
            id: `demo-${Date.now()}`,
            name: 'Demo User',
            email: 'demo@llmhive.ai',
            provider: 'github',
            image: `https://api.dicebear.com/7.x/avataaars/svg?seed=${Date.now()}`,
          }
          setUser(demoUser)
          localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(demoUser))
          return
        }
        
        // Redirect to GitHub OAuth
        const redirectUri = encodeURIComponent(`${window.location.origin}/api/auth/callback/github`)
        const scope = encodeURIComponent('user:email read:user')
        window.location.href = `https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}&redirect_uri=${redirectUri}&scope=${scope}`
      } else if (provider === 'google') {
        if (!GOOGLE_CLIENT_ID) {
          // Demo mode
          toast.info("Demo Mode: Google OAuth not configured. Using demo account.")
          const demoUser: User = {
            id: `demo-${Date.now()}`,
            name: 'Demo User',
            email: 'demo@llmhive.ai',
            provider: 'google',
            image: `https://api.dicebear.com/7.x/avataaars/svg?seed=${Date.now()}`,
          }
          setUser(demoUser)
          localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(demoUser))
          return
        }
        
        // Redirect to Google OAuth
        const redirectUri = encodeURIComponent(`${window.location.origin}/api/auth/callback/google`)
        const scope = encodeURIComponent('email profile')
        window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${GOOGLE_CLIENT_ID}&redirect_uri=${redirectUri}&response_type=code&scope=${scope}`
      }
    } catch (error) {
      console.error('Sign in error:', error)
      toast.error('Sign in failed. Please try again.')
    }
  }, [])

  const signOut = useCallback(async () => {
    try {
      setUser(null)
      localStorage.removeItem(USER_STORAGE_KEY)
      toast.success('Signed out successfully')
    } catch (error) {
      console.error('Sign out error:', error)
      toast.error('Sign out failed')
    }
  }, [])

  const updateProfile = useCallback(async (updates: Partial<User>) => {
    if (!user) return
    
    try {
      const updatedUser = { ...user, ...updates }
      setUser(updatedUser)
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(updatedUser))
      toast.success('Profile updated')
    } catch (error) {
      console.error('Profile update error:', error)
      toast.error('Failed to update profile')
    }
  }, [user])

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    signIn,
    signOut,
    updateProfile,
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

