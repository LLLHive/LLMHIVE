"use client"

import React, { createContext, useContext } from 'react'
import { useUser, useClerk, useAuth as useClerkAuth } from '@clerk/nextjs'

// User type - compatible with Clerk's user object
export interface User {
  id: string
  name: string
  email: string
  image?: string
  provider?: string
}

// Auth context type
interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  signIn: () => void
  signOut: () => Promise<void>
  openUserProfile: () => void
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const { user: clerkUser, isLoaded } = useUser()
  const { signOut: clerkSignOut, openUserProfile, openSignIn } = useClerk()
  const { isSignedIn } = useClerkAuth()

  // Transform Clerk user to our User type
  const user: User | null = clerkUser ? {
    id: clerkUser.id,
    name: clerkUser.fullName || clerkUser.firstName || clerkUser.username || 'User',
    email: clerkUser.primaryEmailAddress?.emailAddress || '',
    image: clerkUser.imageUrl,
    provider: clerkUser.externalAccounts?.[0]?.provider || 'email',
  } : null

  const signIn = () => {
    openSignIn()
  }

  const signOut = async () => {
    await clerkSignOut()
  }

  const value: AuthContextType = {
    user,
    isLoading: !isLoaded,
    isAuthenticated: !!isSignedIn,
    signIn,
    signOut,
    openUserProfile,
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
