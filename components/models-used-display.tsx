"use client"

import { useMemo } from "react"
import Image from "next/image"
import { cn } from "@/lib/utils"
import { getModelById, getModelLogo } from "@/lib/models"
import { Badge } from "@/components/ui/badge"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { Clock, Cpu, Coins } from "lucide-react"

interface ModelsUsedDisplayProps {
  modelIds: string[]
  totalTokens?: number
  latencyMs?: number
  className?: string
  compact?: boolean
}

export function ModelsUsedDisplay({
  modelIds,
  totalTokens,
  latencyMs,
  className,
  compact = false,
}: ModelsUsedDisplayProps) {
  const models = useMemo(() => {
    return modelIds.map((id) => {
      const model = getModelById(id)
      return {
        id,
        name: model?.name || id,
        provider: model?.provider || "unknown",
        logo: model ? getModelLogo(model.provider) : null,
      }
    })
  }, [modelIds])

  if (modelIds.length === 0) {
    return null
  }

  if (compact) {
    return (
      <TooltipProvider>
        <div className={cn("flex items-center gap-1", className)}>
          <span className="text-[10px] text-muted-foreground mr-1">Models:</span>
          <div className="flex -space-x-1">
            {models.slice(0, 3).map((model) => (
              <Tooltip key={model.id}>
                <TooltipTrigger asChild>
                  <div className="relative w-5 h-5 rounded-full bg-secondary border-2 border-background overflow-hidden">
                    {model.logo ? (
                      <Image
                        src={model.logo}
                        alt={model.provider}
                        fill
                        className="object-contain p-0.5"
                      />
                    ) : (
                      <Cpu className="h-3 w-3 m-auto text-muted-foreground" />
                    )}
                  </div>
                </TooltipTrigger>
                <TooltipContent side="top" className="text-xs">
                  {model.name}
                </TooltipContent>
              </Tooltip>
            ))}
          </div>
          {models.length > 3 && (
            <span className="text-[10px] text-muted-foreground ml-1">
              +{models.length - 3}
            </span>
          )}
        </div>
      </TooltipProvider>
    )
  }

  return (
    <div
      className={cn(
        "inline-flex items-center gap-3 px-3 py-2 rounded-lg bg-secondary/50 border border-border",
        className
      )}
    >
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground font-medium">Models Used:</span>
        <div className="flex items-center gap-1.5">
          {models.map((model) => (
            <TooltipProvider key={model.id}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Badge
                    variant="secondary"
                    className="gap-1.5 px-2 py-1 text-xs bg-background hover:bg-background cursor-default"
                  >
                    {model.logo ? (
                      <Image
                        src={model.logo}
                        alt={model.provider}
                        width={14}
                        height={14}
                        className="object-contain"
                      />
                    ) : (
                      <Cpu className="h-3 w-3 text-muted-foreground" />
                    )}
                    <span>{model.name}</span>
                  </Badge>
                </TooltipTrigger>
                <TooltipContent side="top" className="text-xs">
                  Provider: {model.provider}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ))}
        </div>
      </div>

      {/* Stats */}
      {(totalTokens !== undefined || latencyMs !== undefined) && (
        <>
          <div className="w-px h-4 bg-border" />
          <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
            {totalTokens !== undefined && totalTokens > 0 && (
              <span className="flex items-center gap-1">
                <Coins className="h-3 w-3" />
                {totalTokens.toLocaleString()} tokens
              </span>
            )}
            {latencyMs !== undefined && (
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {latencyMs.toLocaleString()}ms
              </span>
            )}
          </div>
        </>
      )}
    </div>
  )
}

