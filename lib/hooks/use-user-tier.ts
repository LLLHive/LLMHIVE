/**
 * User Tier Hook - Fetches the current user's subscription tier
 * 
 * Provides the user's tier for feature gating and model access control.
 * Maps subscription tiers to the UserTier type used by the tier system.
 */
"use client"

import { useState, useEffect } from "react"
import { useUser } from "@clerk/nextjs"
import type { UserTier } from "@/lib/openrouter/tiers"

interface UseUserTierReturn {
  /** The user's tier for model access */
  userTier: UserTier
  /** The raw subscription tier from billing */
  subscriptionTier: string
  /** Stripe/Firestore subscription status (active, trialing, …) */
  subscriptionStatus: string
  /** Whether the tier is still loading */
  isLoading: boolean
  /** Any error that occurred */
  error: string | null
  /** Refresh the tier data */
  refresh: () => void
}

/**
 * Map subscription tier to UserTier for model access control
 * 
 * Subscription tiers: free, lite, pro, enterprise, maximum
 * UserTier (openrouter): free, starter, pro, enterprise
 */
function mapToUserTier(subscriptionTier: string): UserTier {
  const tier = subscriptionTier.toLowerCase()
  
  switch (tier) {
    case "free":
    case "trial":
      return "free"
    case "lite":
    case "starter":
    case "basic":
      return "starter"
    case "pro":
      return "pro"
    case "enterprise":
    case "maximum":
      return "enterprise"
    default:
      return "free"
  }
}

export function useUserTier(): UseUserTierReturn {
  const { isSignedIn, isLoaded } = useUser()
  const [subscriptionTier, setSubscriptionTier] = useState<string>("free")
  const [subscriptionStatus, setSubscriptionStatus] = useState<string>("none")
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchTier = async () => {
    // If not signed in, return free tier
    if (!isSignedIn) {
      setSubscriptionTier("free")
      setIsLoading(false)
      return
    }

    try {
      setIsLoading(true)
      setError(null)

      const response = await fetch("/api/billing/subscription")
      
      if (!response.ok) {
        // Default to free on error
        setSubscriptionTier("free")
        return
      }

      const data = await response.json()
      const tier = data.subscription?.tier || "free"
      const status = data.subscription?.status || "none"
      setSubscriptionTier(tier)
      setSubscriptionStatus(status)
    } catch (err) {
      console.error("[useUserTier] Error fetching tier:", err)
      setError("Failed to fetch subscription tier")
      setSubscriptionTier("free")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    // Wait for Clerk to load before fetching
    if (!isLoaded) return
    
    fetchTier()
  }, [isLoaded, isSignedIn])

  return {
    userTier: mapToUserTier(subscriptionTier),
    subscriptionTier,
    subscriptionStatus,
    isLoading: !isLoaded || isLoading,
    error,
    refresh: fetchTier,
  }
}

/**
 * Get a static tier for server components or when hook can't be used
 * Returns 'free' unless billing proves an active paid subscription.
 */
export function getDefaultTier(): UserTier {
  return "free"
}
