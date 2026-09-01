"use client"

import { cn } from "@/lib/utils"
import { TrendingDown, TrendingUp } from "lucide-react"

export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  trendValue,
  variant = "default",
  className,
}: {
  title: string
  value: string | number
  subtitle?: string
  icon: React.ComponentType<{ className?: string }>
  trend?: "up" | "down" | "neutral"
  trendValue?: string
  variant?: "default" | "bronze" | "success" | "warning" | "danger"
  className?: string
}) {
  const variantStyles = {
    default: "border-border/50",
    bronze: "border-[var(--bronze)]/20 bg-[var(--bronze)]/5",
    success: "border-emerald-500/20 bg-emerald-500/5",
    warning: "border-amber-500/20 bg-amber-500/5",
    danger: "border-red-500/20 bg-red-500/5",
  }

  const iconStyles = {
    default: "text-muted-foreground",
    bronze: "text-[var(--bronze)]",
    success: "text-emerald-500",
    warning: "text-amber-500",
    danger: "text-red-500",
  }

  return (
    <div
      className={cn(
        "rounded-xl border bg-card/50 backdrop-blur-sm p-5 transition-shadow hover:shadow-md",
        variantStyles[variant],
        className
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 min-w-0">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{title}</p>
          <p className="text-2xl font-bold tracking-tight">{value}</p>
          {(subtitle || trendValue) && (
            <div className="flex items-center gap-2 flex-wrap">
              {trend && trendValue && (
                <span
                  className={cn(
                    "inline-flex items-center gap-0.5 text-xs font-medium",
                    trend === "up" && "text-emerald-500",
                    trend === "down" && "text-red-500",
                    trend === "neutral" && "text-muted-foreground"
                  )}
                >
                  {trend === "up" && <TrendingUp className="h-3 w-3" />}
                  {trend === "down" && <TrendingDown className="h-3 w-3" />}
                  {trendValue}
                </span>
              )}
              {subtitle && <span className="text-xs text-muted-foreground">{subtitle}</span>}
            </div>
          )}
        </div>
        <div className={cn("rounded-lg bg-muted/50 p-2.5", iconStyles[variant])}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  )
}
