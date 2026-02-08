"use client"

import { useState } from "react"
import { Sliders, Target, Zap, Palette } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Slider } from "@/components/ui/slider"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import type { CriteriaSettings } from "@/lib/types"
import { cn } from "@/lib/utils"

interface CriteriaEqualizerProps {
  settings: CriteriaSettings
  onChange: (settings: CriteriaSettings) => void
}

export function CriteriaEqualizer({ settings, onChange }: CriteriaEqualizerProps) {
  const [open, setOpen] = useState(false)

  const presets = [
    { name: "Balanced", accuracy: 70, speed: 70, creativity: 50 },
    { name: "Fast", accuracy: 50, speed: 100, creativity: 30 },
    { name: "Precise", accuracy: 100, speed: 30, creativity: 40 },
    { name: "Creative", accuracy: 60, speed: 60, creativity: 100 },
  ]

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={cn(
            "gap-2 h-6 px-2 text-[10px] sm:h-7 sm:px-2.5 sm:text-[11px] bg-transparent border border-border rounded-md text-foreground transition-all duration-300 [&:hover]:bg-[#cd7f32] [&:hover]:border-[#cd7f32] [&:hover]:text-black touch-target",
            open && "bg-[#cd7f32] border-[#cd7f32] text-black",
          )}
        >
          <Sliders className="h-3.5 w-3.5" />
          <span className="text-[10px] sm:text-[11px] font-display text-white/80">Tuning</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-[90vw] sm:w-80 z-[600]" align="start">
        <div className="space-y-3 sm:space-y-4">
          <div>
            <h4 className="font-semibold text-[13px] sm:text-sm mb-1">Dynamic Criteria Equalizer</h4>
            <p className="text-[11px] sm:text-xs text-muted-foreground">
              Adjust how the AI hive balances accuracy, speed, and creativity
            </p>
          </div>

          {/* Presets */}
          <div className="grid grid-cols-4 gap-2">
            {presets.map((preset) => (
              <Button
                key={preset.name}
                variant="outline"
                size="sm"
                className="text-[10px] sm:text-xs h-auto py-2 bg-transparent"
                onClick={() => onChange(preset)}
              >
                {preset.name}
              </Button>
            ))}
          </div>

          {/* Accuracy Slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded bg-blue-500/20 flex items-center justify-center">
                  <Target className="h-3 w-3 text-blue-500" />
                </div>
                <span className="text-[12px] sm:text-sm font-medium">Accuracy</span>
              </div>
              <span className="text-[11px] sm:text-xs text-muted-foreground">{settings.accuracy}%</span>
            </div>
            <Slider
              value={[settings.accuracy]}
              onValueChange={([value]) => onChange({ ...settings, accuracy: value })}
              max={100}
              step={10}
              className="[&_[role=slider]]:bg-blue-500 [&_[role=slider]]:border-blue-500"
            />
          </div>

          {/* Speed Slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded bg-green-500/20 flex items-center justify-center">
                  <Zap className="h-3 w-3 text-green-500" />
                </div>
                <span className="text-[12px] sm:text-sm font-medium">Speed</span>
              </div>
              <span className="text-[11px] sm:text-xs text-muted-foreground">{settings.speed}%</span>
            </div>
            <Slider
              value={[settings.speed]}
              onValueChange={([value]) => onChange({ ...settings, speed: value })}
              max={100}
              step={10}
              className="[&_[role=slider]]:bg-green-500 [&_[role=slider]]:border-green-500"
            />
          </div>

          {/* Creativity Slider */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded bg-purple-500/20 flex items-center justify-center">
                  <Palette className="h-3 w-3 text-purple-500" />
                </div>
                <span className="text-[12px] sm:text-sm font-medium">Creativity</span>
              </div>
              <span className="text-[11px] sm:text-xs text-muted-foreground">{settings.creativity}%</span>
            </div>
            <Slider
              value={[settings.creativity]}
              onValueChange={([value]) => onChange({ ...settings, creativity: value })}
              max={100}
              step={10}
              className="[&_[role=slider]]:bg-purple-500 [&_[role=slider]]:border-purple-500"
            />
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}
