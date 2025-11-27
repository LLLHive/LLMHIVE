import type React from "react"
import { cn } from "@/lib/utils"

interface DiscoverCardProps {
  icon: React.ComponentType<{ className?: string }>
  title: string
  description: string
  color: string
}

export function DiscoverCard({ icon: Icon, title, description, color }: DiscoverCardProps) {
  return (
    <div className="p-4 rounded-lg border border-border bg-card hover:border-[var(--bronze)] transition-colors cursor-pointer">
      <div className="flex items-start gap-3">
        <div className={cn("w-10 h-10 rounded-lg bg-gradient-to-br flex items-center justify-center", color)}>
          <Icon className="h-5 w-5 text-white" />
        </div>
        <div className="flex-1">
          <h4 className="font-semibold text-sm mb-1">{title}</h4>
          <p className="text-xs text-muted-foreground">{description}</p>
        </div>
      </div>
    </div>
  )
}
