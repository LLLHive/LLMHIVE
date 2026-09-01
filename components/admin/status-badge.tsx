"use client"

import { cn } from "@/lib/utils"
import { Badge } from "@/components/ui/badge"
import type { ProviderStatus } from "@/lib/admin/types"

const STATUS_CONFIG: Record<
  ProviderStatus,
  { label: string; dotClass: string; badgeClass: string }
> = {
  healthy: {
    label: "Healthy",
    dotClass: "bg-emerald-500 shadow-emerald-500/50",
    badgeClass: "border-emerald-500/30 text-emerald-500 bg-emerald-500/10",
  },
  degraded: {
    label: "Degraded",
    dotClass: "bg-amber-500 shadow-amber-500/50",
    badgeClass: "border-amber-500/30 text-amber-500 bg-amber-500/10",
  },
  down: {
    label: "Down",
    dotClass: "bg-red-500 shadow-red-500/50",
    badgeClass: "border-red-500/30 text-red-500 bg-red-500/10",
  },
  throttled: {
    label: "Throttled",
    dotClass: "bg-orange-500 shadow-orange-500/50 animate-pulse",
    badgeClass: "border-orange-500/30 text-orange-500 bg-orange-500/10",
  },
  unconfigured: {
    label: "Not configured",
    dotClass: "bg-muted-foreground/50",
    badgeClass: "border-muted-foreground/30 text-muted-foreground bg-muted/50",
  },
}

export function StatusBadge({
  status,
  showDot = true,
  size = "default",
}: {
  status: ProviderStatus
  showDot?: boolean
  size?: "default" | "sm"
}) {
  const config = STATUS_CONFIG[status]

  return (
    <Badge
      variant="outline"
      className={cn(
        "font-medium gap-1.5",
        config.badgeClass,
        size === "sm" && "text-[10px] px-1.5 py-0"
      )}
    >
      {showDot && (
        <span
          className={cn(
            "inline-block h-1.5 w-1.5 rounded-full shadow-sm",
            config.dotClass,
            status === "healthy" && "animate-pulse"
          )}
        />
      )}
      {config.label}
    </Badge>
  )
}

export function ConnectionTypeBadge({ type }: { type: "direct" | "aggregator" }) {
  return (
    <Badge
      variant="secondary"
      className={cn(
        "text-[10px] uppercase tracking-wide font-semibold",
        type === "direct"
          ? "bg-blue-500/10 text-blue-400 border-blue-500/20"
          : "bg-purple-500/10 text-purple-400 border-purple-500/20"
      )}
    >
      {type === "direct" ? "Direct API" : "Aggregator"}
    </Badge>
  )
}
