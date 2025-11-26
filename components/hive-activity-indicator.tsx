"use client"

import { useEffect, useState } from "react"
import { cn } from "@/lib/utils"

interface HiveActivityIndicatorProps {
  active: boolean
  agentCount?: number
}

export function HiveActivityIndicator({ active, agentCount = 6 }: HiveActivityIndicatorProps) {
  const [pulseIndex, setPulseIndex] = useState(0)

  useEffect(() => {
    if (!active) return
    const interval = setInterval(() => {
      setPulseIndex((prev) => (prev + 1) % agentCount)
    }, 300)
    return () => clearInterval(interval)
  }, [active, agentCount])

  if (!active) return null

  return (
    <div className="flex items-center gap-2 px-4 py-2 bg-[var(--bronze)]/5 border-b border-[var(--bronze)]/10">
      <div className="flex items-center gap-1">
        {Array.from({ length: agentCount }).map((_, i) => (
          <div
            key={i}
            className={cn(
              "w-2 h-2 rounded-sm transition-all duration-300",
              i === pulseIndex ? "bg-[var(--bronze)] scale-125 rotate-45" : "bg-[var(--bronze)]/30 rotate-45",
            )}
            style={{
              clipPath: "polygon(30% 0%, 70% 0%, 100% 30%, 100% 70%, 70% 100%, 30% 100%, 0% 70%, 0% 30%)",
            }}
          />
        ))}
      </div>
      <span className="text-xs text-[var(--bronze)] font-medium animate-pulse">Hive mind processing...</span>
    </div>
  )
}
