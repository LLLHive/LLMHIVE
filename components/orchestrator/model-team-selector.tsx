"use client"

import React, { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Slider } from "@/components/ui/slider"
import { 
  Users, 
  Plus, 
  X, 
  Crown, 
  Shield, 
  Zap, 
  Star,
  GripVertical,
} from "lucide-react"
import { getModelById, AVAILABLE_MODELS } from "@/lib/models"
import type { ModelRole, ModelTeamMember, EliteStrategy } from "@/lib/openrouter/types"

// Role configuration
const ROLE_CONFIG: Record<ModelRole, { label: string; icon: React.ElementType; color: string; description: string }> = {
  primary: { label: "Primary", icon: Crown, color: "text-yellow-500", description: "Main response generator" },
  validator: { label: "Validator", icon: Shield, color: "text-blue-500", description: "Validates and critiques" },
  fallback: { label: "Fallback", icon: Zap, color: "text-green-500", description: "Used if primary fails" },
  specialist: { label: "Specialist", icon: Star, color: "text-purple-500", description: "Domain expert" },
}

interface ModelTeamSelectorProps {
  team: ModelTeamMember[]
  onTeamChange: (team: ModelTeamMember[]) => void
  strategy: EliteStrategy
  onStrategyChange: (strategy: EliteStrategy) => void
  maxMembers?: number
}

/**
 * PR6: Model Team Selector Component
 * 
 * Allows users to build a custom team of models with assigned roles
 * for orchestration.
 */
export function ModelTeamSelector({
  team,
  onTeamChange,
  strategy,
  onStrategyChange,
  maxMembers = 5,
}: ModelTeamSelectorProps) {
  const [showAddModal, setShowAddModal] = useState(false)

  const addMember = (modelId: string, role: ModelRole) => {
    if (team.length >= maxMembers) return
    if (team.some(m => m.modelId === modelId)) return
    
    onTeamChange([
      ...team,
      { modelId, role, weight: 1.0 }
    ])
  }

  const removeMember = (modelId: string) => {
    onTeamChange(team.filter(m => m.modelId !== modelId))
  }

  const updateMemberRole = (modelId: string, role: ModelRole) => {
    onTeamChange(team.map(m => 
      m.modelId === modelId ? { ...m, role } : m
    ))
  }

  const updateMemberWeight = (modelId: string, weight: number) => {
    onTeamChange(team.map(m =>
      m.modelId === modelId ? { ...m, weight } : m
    ))
  }

  // Get available models not in team
  const availableModels = AVAILABLE_MODELS.filter(
    model => !team.some(m => m.modelId === model.id) && model.id !== "automatic"
  )

  return (
    <Card className="border-border/50 bg-card/50">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Users className="h-4 w-4 text-[var(--bronze)]" />
            <CardTitle className="text-sm font-medium">Model Team</CardTitle>
          </div>
          <Badge variant="outline" className="text-xs">
            {team.length}/{maxMembers}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Strategy Selector */}
        <div className="space-y-1">
          <label className="text-xs text-muted-foreground">Strategy</label>
          <Select value={strategy} onValueChange={(v) => onStrategyChange(v as EliteStrategy)}>
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder="Select strategy" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="automatic">Automatic</SelectItem>
              <SelectItem value="single_best">Single Best</SelectItem>
              <SelectItem value="parallel_race">Parallel Race</SelectItem>
              <SelectItem value="best_of_n">Best of N</SelectItem>
              <SelectItem value="quality_weighted_fusion">Quality Weighted Fusion</SelectItem>
              <SelectItem value="expert_panel">Expert Panel</SelectItem>
              <SelectItem value="challenge_and_refine">Challenge & Refine</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Team Members */}
        <ScrollArea className="h-[200px]">
          <div className="space-y-2">
            {team.map((member, index) => {
              const model = getModelById(member.modelId)
              const roleConfig = ROLE_CONFIG[member.role]
              const RoleIcon = roleConfig?.icon || Star
              
              return (
                <div 
                  key={member.modelId}
                  className="p-2 rounded-lg bg-secondary/50 border border-border/50 space-y-2"
                >
                  <div className="flex items-center gap-2">
                    <GripVertical className="h-3 w-3 text-muted-foreground cursor-grab" />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-medium">
                          {model?.name || member.modelId}
                        </span>
                        <Badge 
                          variant="secondary" 
                          className={`text-[10px] gap-1 ${roleConfig?.color || ""}`}
                        >
                          <RoleIcon className="h-2.5 w-2.5" />
                          {roleConfig?.label || member.role}
                        </Badge>
                      </div>
                      <p className="text-[10px] text-muted-foreground">
                        {model?.description?.slice(0, 50) || roleConfig?.description}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      onClick={() => removeMember(member.modelId)}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                  
                  {/* Role & Weight Controls */}
                  <div className="flex items-center gap-3">
                    <Select 
                      value={member.role} 
                      onValueChange={(v) => updateMemberRole(member.modelId, v as ModelRole)}
                    >
                      <SelectTrigger className="h-6 text-[10px] w-24">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(ROLE_CONFIG).map(([role, config]) => (
                          <SelectItem key={role} value={role} className="text-xs">
                            <div className="flex items-center gap-1">
                              <config.icon className={`h-3 w-3 ${config.color}`} />
                              {config.label}
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    
                    {strategy === "quality_weighted_fusion" && (
                      <div className="flex items-center gap-2 flex-1">
                        <span className="text-[10px] text-muted-foreground">Weight</span>
                        <Slider
                          value={[member.weight || 1.0]}
                          onValueChange={([v]) => updateMemberWeight(member.modelId, v)}
                          min={0}
                          max={1}
                          step={0.1}
                          className="w-16"
                        />
                        <span className="text-[10px] w-6">
                          {(member.weight || 1.0).toFixed(1)}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )
            })}

            {team.length === 0 && (
              <div className="flex flex-col items-center justify-center py-6 text-muted-foreground">
                <Users className="h-8 w-8 mb-2 opacity-50" />
                <p className="text-xs">No models in team</p>
                <p className="text-[10px]">Add models below to build your team</p>
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Add Member */}
        {team.length < maxMembers && (
          <div className="space-y-2">
            <Select 
              onValueChange={(modelId) => addMember(modelId, "primary")}
            >
              <SelectTrigger className="h-8 text-xs">
                <div className="flex items-center gap-2">
                  <Plus className="h-3 w-3" />
                  <span>Add model to team</span>
                </div>
              </SelectTrigger>
              <SelectContent>
                {availableModels.length > 0 ? (
                  availableModels.map(model => (
                    <SelectItem key={model.id} value={model.id} className="text-xs">
                      <div className="flex items-center gap-2">
                        <span>{model.name}</span>
                        {model.category && (
                          <Badge variant="outline" className="text-[10px]">
                            {model.category}
                          </Badge>
                        )}
                      </div>
                    </SelectItem>
                  ))
                ) : (
                  <div className="p-2 text-xs text-muted-foreground text-center">
                    All available models are in the team
                  </div>
                )}
              </SelectContent>
            </Select>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default ModelTeamSelector

