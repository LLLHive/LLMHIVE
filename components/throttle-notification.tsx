"use client"

import { useState, useEffect } from "react"
import { useUser } from "@clerk/nextjs"
import { AlertTriangle, Zap, X, ArrowUpRight } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import Link from "next/link"

interface ThrottleStatus {
  is_throttled: boolean
  subscription_tier: string
  current_orchestration: string
  elite_queries_limit: number
  elite_queries_used: number
  elite_queries_remaining: number
  throttle_message: string | null
  upgrade_url: string
}

interface ThrottleNotificationProps {
  className?: string
  variant?: "banner" | "inline" | "toast"
}

export function ThrottleNotification({ 
  className, 
  variant = "banner" 
}: ThrottleNotificationProps) {
  const { user, isLoaded } = useUser()
  const [throttleStatus, setThrottleStatus] = useState<ThrottleStatus | null>(null)
  const [dismissed, setDismissed] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchThrottleStatus = async () => {
      if (!isLoaded || !user) {
        setLoading(false)
        return
      }

      try {
        const response = await fetch(`/api/billing/throttle-status?userId=${user.id}`)
        if (response.ok) {
          const data = await response.json()
          setThrottleStatus(data)
        }
      } catch (error) {
        console.error("Failed to fetch throttle status:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchThrottleStatus()
  }, [user, isLoaded])

  // Don't show if loading, dismissed, not loaded, or not throttled
  if (loading || dismissed || !isLoaded || !throttleStatus?.is_throttled) {
    return null
  }

  const handleDismiss = () => {
    setDismissed(true)
    // Remember dismissal for this session
    sessionStorage.setItem("throttle-notification-dismissed", "true")
  }

  if (variant === "banner") {
    return (
      <div className={cn(
        "relative w-full bg-gradient-to-r from-amber-500/90 to-orange-500/90 text-white px-4 py-2",
        className
      )}>
        <div className="container mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 shrink-0" />
            <p className="text-sm font-medium">
              <span className="font-semibold">ELITE quota exhausted.</span>{" "}
              You're now using FREE orchestration. 
              <span className="hidden sm:inline"> Upgrade to restore #1 quality.</span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/pricing">
              <Button 
                size="sm" 
                className="bg-white text-amber-600 hover:bg-white/90 font-semibold"
              >
                <Zap className="h-4 w-4 mr-1" />
                Upgrade Now
              </Button>
            </Link>
            <button
              onClick={handleDismiss}
              className="p-1 hover:bg-white/20 rounded transition-colors"
              aria-label="Dismiss"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (variant === "inline") {
    return (
      <div className={cn(
        "rounded-lg border border-amber-500/50 bg-amber-500/10 p-4",
        className
      )}>
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
          <div className="flex-1 space-y-2">
            <p className="text-sm font-medium text-amber-200">
              ELITE Quota Exhausted
            </p>
            <p className="text-sm text-muted-foreground">
              You've used all {throttleStatus.elite_queries_used} of your ELITE queries. 
              You're now using FREE orchestration, which still beats most single models!
            </p>
            <Link href="/pricing">
              <Button 
                size="sm" 
                variant="outline"
                className="border-amber-500/50 text-amber-400 hover:bg-amber-500/10"
              >
                Upgrade for More ELITE Queries
                <ArrowUpRight className="h-4 w-4 ml-1" />
              </Button>
            </Link>
          </div>
          <button
            onClick={handleDismiss}
            className="p-1 hover:bg-white/10 rounded transition-colors"
            aria-label="Dismiss"
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        </div>
      </div>
    )
  }

  // Toast variant
  return (
    <div className={cn(
      "fixed bottom-4 right-4 z-50 max-w-sm rounded-lg border border-amber-500/50 bg-background shadow-lg",
      className
    )}>
      <div className="p-4">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-full bg-amber-500/20">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
          </div>
          <div className="flex-1 space-y-1">
            <p className="text-sm font-semibold">ELITE Quota Exhausted</p>
            <p className="text-xs text-muted-foreground">
              Using FREE orchestration. Upgrade for #1 quality.
            </p>
          </div>
          <button
            onClick={handleDismiss}
            className="p-1 hover:bg-muted rounded transition-colors"
            aria-label="Dismiss"
          >
            <X className="h-4 w-4 text-muted-foreground" />
          </button>
        </div>
        <div className="mt-3 flex gap-2">
          <Link href="/pricing" className="flex-1">
            <Button size="sm" className="w-full bg-amber-500 hover:bg-amber-600 text-black">
              Upgrade Now
            </Button>
          </Link>
          <Button 
            size="sm" 
            variant="ghost" 
            onClick={handleDismiss}
            className="text-muted-foreground"
          >
            Later
          </Button>
        </div>
      </div>
    </div>
  )
}

// Quota status indicator for sidebar/header
export function QuotaIndicator({ className }: { className?: string }) {
  const { user, isLoaded } = useUser()
  const [throttleStatus, setThrottleStatus] = useState<ThrottleStatus | null>(null)

  useEffect(() => {
    const fetchThrottleStatus = async () => {
      if (!isLoaded || !user) return

      try {
        const response = await fetch(`/api/billing/throttle-status?userId=${user.id}`)
        if (response.ok) {
          const data = await response.json()
          setThrottleStatus(data)
        }
      } catch (error) {
        console.error("Failed to fetch throttle status:", error)
      }
    }

    fetchThrottleStatus()
  }, [user, isLoaded])

  if (!throttleStatus) return null

  const isThrottled = throttleStatus.is_throttled
  const remaining = throttleStatus.elite_queries_remaining
  const limit = throttleStatus.elite_queries_limit
  const tier = throttleStatus.subscription_tier

  // FREE tier doesn't show quota (they don't have ELITE)
  if (tier === "free") {
    return (
      <div className={cn("flex items-center gap-2 text-xs", className)}>
        <div className="w-2 h-2 rounded-full bg-green-500" />
        <span className="text-muted-foreground">FREE tier</span>
      </div>
    )
  }

  // Throttled state
  if (isThrottled) {
    return (
      <Link href="/pricing">
        <div className={cn(
          "flex items-center gap-2 text-xs px-2 py-1 rounded-md bg-amber-500/10 text-amber-400 cursor-pointer hover:bg-amber-500/20 transition-colors",
          className
        )}>
          <AlertTriangle className="h-3 w-3" />
          <span>ELITE exhausted</span>
          <ArrowUpRight className="h-3 w-3" />
        </div>
      </Link>
    )
  }

  // Normal state with quota
  const percentRemaining = limit > 0 ? (remaining / limit) * 100 : 100
  const isLow = percentRemaining < 20

  return (
    <div className={cn("flex items-center gap-2 text-xs", className)}>
      <div className={cn(
        "w-2 h-2 rounded-full",
        isLow ? "bg-yellow-500" : "bg-green-500"
      )} />
      <span className="text-muted-foreground">
        {remaining === -1 ? "Unlimited" : `${remaining}/${limit}`} ELITE
      </span>
    </div>
  )
}
