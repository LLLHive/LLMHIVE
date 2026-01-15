"use client"

import { useState, useEffect } from "react"
import { AlertTriangle, X, Zap, TrendingUp } from "lucide-react"
import { Button } from "@/components/ui/button"
import Link from "next/link"

interface UsageData {
  percentUsed: number
  status: "normal" | "warning" | "throttled" | "blocked"
  modelRestriction?: "none" | "premium_blocked" | "standard_only" | "budget_only"
  message?: string
  daysUntilReset: number
  tier: string
}

export function UsageAlert() {
  const [usageData, setUsageData] = useState<UsageData | null>(null)
  const [dismissed, setDismissed] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchUsage() {
      try {
        const response = await fetch("/api/billing/usage")
        if (response.ok) {
          const data = await response.json()
          setUsageData(data)
        }
      } catch (error) {
        console.error("Failed to fetch usage:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchUsage()
    // Refresh every 5 minutes
    const interval = setInterval(fetchUsage, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  // Don't show if loading, dismissed, or normal status
  if (loading || dismissed || !usageData || usageData.status === "normal") {
    return null
  }

  const getAlertStyle = () => {
    switch (usageData.status) {
      case "blocked":
        return "bg-red-500/10 border-red-500/30 text-red-400"
      case "throttled":
        return "bg-amber-500/10 border-amber-500/30 text-amber-400"
      case "warning":
        return "bg-yellow-500/10 border-yellow-500/30 text-yellow-400"
      default:
        return "bg-blue-500/10 border-blue-500/30 text-blue-400"
    }
  }

  const getIcon = () => {
    switch (usageData.status) {
      case "blocked":
        return <AlertTriangle className="h-5 w-5 text-red-400" />
      case "throttled":
        return <TrendingUp className="h-5 w-5 text-amber-400" />
      case "warning":
        return <Zap className="h-5 w-5 text-yellow-400" />
      default:
        return <Zap className="h-5 w-5 text-blue-400" />
    }
  }

  const getTitle = () => {
    switch (usageData.status) {
      case "blocked":
        return "Usage Limit Reached"
      case "throttled":
        return "High Usage - Performance Optimized"
      case "warning":
        return "Usage Notice"
      default:
        return "Usage Update"
    }
  }

  const percentDisplay = Math.round(usageData.percentUsed * 100)

  return (
    <div
      className={`fixed bottom-4 right-4 z-50 max-w-md rounded-lg border p-4 shadow-lg backdrop-blur-sm ${getAlertStyle()}`}
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-0.5">{getIcon()}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2">
            <h4 className="font-semibold text-sm">{getTitle()}</h4>
            <button
              onClick={() => setDismissed(true)}
              className="text-current/50 hover:text-current transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          
          <p className="text-sm mt-1 opacity-90">
            {usageData.message}
          </p>
          
          {/* Usage bar */}
          <div className="mt-3">
            <div className="flex justify-between text-xs mb-1">
              <span>{percentDisplay}% used</span>
              <span>{usageData.daysUntilReset} days until reset</span>
            </div>
            <div className="h-2 bg-black/20 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  percentDisplay >= 100
                    ? "bg-red-500"
                    : percentDisplay >= 90
                    ? "bg-amber-500"
                    : percentDisplay >= 75
                    ? "bg-yellow-500"
                    : "bg-emerald-500"
                }`}
                style={{ width: `${Math.min(percentDisplay, 100)}%` }}
              />
            </div>
          </div>

          {/* Model restriction notice */}
          {usageData.modelRestriction && usageData.modelRestriction !== "none" && (
            <p className="text-xs mt-2 opacity-75">
              {usageData.modelRestriction === "budget_only" && (
                <>Currently using budget-efficient models (Llama, DeepSeek, Gemini Flash)</>
              )}
              {usageData.modelRestriction === "standard_only" && (
                <>Premium models temporarily unavailable to preserve your allowance</>
              )}
              {usageData.modelRestriction === "premium_blocked" && (
                <>Flagship models (GPT-5.2 Pro, o1-pro) unavailable until next cycle</>
              )}
            </p>
          )}

          {/* Upgrade CTA */}
          {(usageData.status === "warning" || usageData.status === "throttled" || usageData.status === "blocked") && (
            <div className="mt-3 flex gap-2">
              <Link href="/pricing">
                <Button
                  size="sm"
                  variant="secondary"
                  className="text-xs"
                >
                  Upgrade Plan
                </Button>
              </Link>
              {usageData.status === "blocked" && (
                <Link href="/api/billing/portal">
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-xs"
                  >
                    Add Overage
                  </Button>
                </Link>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

// Mini version for inline display in chat
export function UsageIndicator({ className = "" }: { className?: string }) {
  const [usageData, setUsageData] = useState<UsageData | null>(null)

  useEffect(() => {
    async function fetchUsage() {
      try {
        const response = await fetch("/api/billing/usage")
        if (response.ok) {
          const data = await response.json()
          setUsageData(data)
        }
      } catch (error) {
        console.error("Failed to fetch usage:", error)
      }
    }

    fetchUsage()
  }, [])

  if (!usageData) return null

  const percentDisplay = Math.round(usageData.percentUsed * 100)
  
  const getColor = () => {
    if (percentDisplay >= 100) return "text-red-400"
    if (percentDisplay >= 90) return "text-amber-400"
    if (percentDisplay >= 75) return "text-yellow-400"
    return "text-emerald-400"
  }

  return (
    <div className={`flex items-center gap-2 text-xs ${className}`}>
      <div className="w-16 h-1.5 bg-white/10 rounded-full overflow-hidden">
        <div
          className={`h-full ${
            percentDisplay >= 100
              ? "bg-red-400"
              : percentDisplay >= 90
              ? "bg-amber-400"
              : percentDisplay >= 75
              ? "bg-yellow-400"
              : "bg-emerald-400"
          }`}
          style={{ width: `${Math.min(percentDisplay, 100)}%` }}
        />
      </div>
      <span className={getColor()}>{percentDisplay}%</span>
    </div>
  )
}
