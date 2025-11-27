"use client"

import type React from "react"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  Brain,
  Sparkles,
  X,
  Check,
  AlertCircle,
  Save,
  RotateCcw,
  Zap,
  Code,
  Calculator,
  Lightbulb,
  Eye,
} from "lucide-react"
import Link from "next/link"
import Image from "next/image"
import {
  REASONING_CATEGORIES,
  getMethodsByCategory,
  type ReasoningCategory,
  type ReasoningMethodData,
} from "@/lib/reasoning-methods"

type ReasoningMode = "auto" | "manual"

const CATEGORY_ICONS: Record<ReasoningCategory, React.ReactNode> = {
  "General Reasoning": <Brain className="h-4 w-4" />,
  "Code Generation & Reasoning": <Code className="h-4 w-4" />,
  "Mathematical Reasoning": <Calculator className="h-4 w-4" />,
  "Commonsense & Logical Reasoning": <Lightbulb className="h-4 w-4" />,
  "Multi-Modal Reasoning": <Eye className="h-4 w-4" />,
}

export default function ReasoningSettingsPage() {
  const [mode, setMode] = useState<ReasoningMode>("auto")
  const [selectedCategory, setSelectedCategory] = useState<ReasoningCategory>("General Reasoning")
  const [selectedMethods, setSelectedMethods] = useState<ReasoningMethodData[]>([])
  const [isSaving, setIsSaving] = useState(false)
  const [saveSuccess, setSaveSuccess] = useState(false)

  const categoryMethods = getMethodsByCategory(selectedCategory)

  const toggleMethod = (method: ReasoningMethodData) => {
    setSelectedMethods((prev) => {
      const isSelected = prev.some((m) => m.id === method.id)
      if (isSelected) {
        return prev.filter((m) => m.id !== method.id)
      } else {
        return [...prev, method]
      }
    })
  }

  const removeMethod = (methodId: string) => {
    setSelectedMethods((prev) => prev.filter((m) => m.id !== methodId))
  }

  const handleSave = async () => {
    setIsSaving(true)
    setSaveSuccess(false)

    try {
      const response = await fetch("/api/reasoning-config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode,
          selectedMethods: selectedMethods.map((m) => ({
            id: m.id,
            name: m.name,
            category: m.category,
          })),
        }),
      })

      if (response.ok) {
        setSaveSuccess(true)
        setTimeout(() => setSaveSuccess(false), 3000)
      }
    } catch (error) {
      console.error("Failed to save reasoning config:", error)
    } finally {
      setIsSaving(false)
    }
  }

  const handleResetToAuto = () => {
    setMode("auto")
    setSelectedMethods([])
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-14 items-center gap-4 px-4">
          <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <Image src="/logo.png" alt="LLMHive" width={32} height={32} className="rounded-lg" />
            <span className="font-semibold text-[var(--bronze)]">LLMHive</span>
          </Link>
          <div className="h-6 w-px bg-border" />
          <div className="flex items-center gap-2">
            <Brain className="h-5 w-5 text-[var(--bronze)]" />
            <h1 className="text-lg font-semibold">Advanced Reasoning Settings</h1>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={handleResetToAuto}
              className="text-muted-foreground hover:text-foreground"
            >
              <RotateCcw className="h-4 w-4 mr-2" />
              Reset to Auto
            </Button>
            <Button
              onClick={handleSave}
              disabled={isSaving}
              className="bg-[var(--bronze)] hover:bg-[var(--bronze-dark)] text-black"
            >
              {isSaving ? (
                <>
                  <div className="h-4 w-4 mr-2 animate-spin rounded-full border-2 border-black border-t-transparent" />
                  Saving...
                </>
              ) : saveSuccess ? (
                <>
                  <Check className="h-4 w-4 mr-2" />
                  Saved!
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Save / Apply
                </>
              )}
            </Button>
          </div>
        </div>
      </header>

      <main className="container px-4 py-6">
        <div className="grid gap-6 lg:grid-cols-[400px_1fr]">
          {/* Left Panel - Controls */}
          <div className="space-y-6">
            {/* Mode Selector */}
            <Card className="border-border bg-card">
              <CardHeader className="pb-3">
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Zap className="h-5 w-5 text-[var(--bronze)]" />
                  Reasoning Mode
                </CardTitle>
                <CardDescription>Choose how the orchestrator selects reasoning methods</CardDescription>
              </CardHeader>
              <CardContent>
                <RadioGroup value={mode} onValueChange={(v) => setMode(v as ReasoningMode)} className="space-y-3">
                  <div className="flex items-start space-x-3 rounded-lg border border-border p-3 hover:bg-muted/50 transition-colors">
                    <RadioGroupItem value="auto" id="auto" className="mt-0.5" />
                    <div className="flex-1">
                      <Label htmlFor="auto" className="flex items-center gap-2 cursor-pointer font-medium">
                        <Sparkles className="h-4 w-4 text-[var(--bronze)]" />
                        Auto (recommended)
                      </Label>
                      <p className="text-sm text-muted-foreground mt-1">
                        The orchestrator will automatically select the best reasoning methods based on the prompt,
                        target task, and available LLMs.
                      </p>
                    </div>
                  </div>
                  <div className="flex items-start space-x-3 rounded-lg border border-border p-3 hover:bg-muted/50 transition-colors">
                    <RadioGroupItem value="manual" id="manual" className="mt-0.5" />
                    <div className="flex-1">
                      <Label htmlFor="manual" className="flex items-center gap-2 cursor-pointer font-medium">
                        <Brain className="h-4 w-4 text-[var(--bronze)]" />
                        Manual
                      </Label>
                      <p className="text-sm text-muted-foreground mt-1">
                        Explicitly choose which reasoning categories and methods to use.
                      </p>
                    </div>
                  </div>
                </RadioGroup>
              </CardContent>
            </Card>

            {/* Category & Method Selection - Only visible in Manual mode */}
            {mode === "manual" && (
              <>
                {/* Category Dropdown */}
                <Card className="border-border bg-card">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">Reasoning Category</CardTitle>
                    <CardDescription>Select a category to view available methods</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Select value={selectedCategory} onValueChange={(v) => setSelectedCategory(v as ReasoningCategory)}>
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {REASONING_CATEGORIES.map((category) => (
                          <SelectItem key={category} value={category}>
                            <div className="flex items-center gap-2">
                              {CATEGORY_ICONS[category]}
                              {category}
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </CardContent>
                </Card>

                {/* Method Selection */}
                <Card className="border-border bg-card">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">Reasoning Methods</CardTitle>
                    <CardDescription>Select one or more methods from {selectedCategory}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ScrollArea className="h-[300px] pr-4">
                      <div className="space-y-2">
                        {categoryMethods.map((method) => {
                          const isSelected = selectedMethods.some((m) => m.id === method.id)
                          return (
                            <div
                              key={method.id}
                              className={`flex items-start space-x-3 rounded-lg border p-3 cursor-pointer transition-colors ${
                                isSelected
                                  ? "border-[var(--bronze)] bg-[var(--bronze)]/10"
                                  : "border-border hover:bg-muted/50"
                              }`}
                              onClick={() => toggleMethod(method)}
                            >
                              <Checkbox checked={isSelected} className="mt-0.5" />
                              <div className="flex-1 min-w-0">
                                <p className="font-medium text-sm">{method.name}</p>
                                <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                                  {method.shortDescription}
                                </p>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </ScrollArea>
                  </CardContent>
                </Card>
              </>
            )}

            {/* Summary */}
            <Card className="border-border bg-card">
              <CardContent className="pt-6">
                <div className="flex items-center gap-2 text-sm">
                  <AlertCircle className="h-4 w-4 text-muted-foreground" />
                  {mode === "auto" ? (
                    <span className="text-muted-foreground">
                      Reasoning mode: <span className="text-foreground font-medium">Auto</span> (orchestrator chooses
                      methods)
                    </span>
                  ) : (
                    <span className="text-muted-foreground">
                      Reasoning mode: <span className="text-foreground font-medium">Manual</span>.{" "}
                      <span className="text-[var(--bronze)] font-medium">{selectedMethods.length}</span> method
                      {selectedMethods.length !== 1 ? "s" : ""} selected.
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Right Panel - Method Details */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Selected Methods</h2>
              {selectedMethods.length > 0 && (
                <Badge variant="outline" className="border-[var(--bronze)] text-[var(--bronze)]">
                  {selectedMethods.length} selected
                </Badge>
              )}
            </div>

            {mode === "auto" ? (
              <Card className="border-border bg-card">
                <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                  <div className="rounded-full bg-[var(--bronze)]/10 p-4 mb-4">
                    <Sparkles className="h-8 w-8 text-[var(--bronze)]" />
                  </div>
                  <h3 className="font-semibold text-lg mb-2">Auto Mode Enabled</h3>
                  <p className="text-muted-foreground max-w-md">
                    The orchestrator will automatically analyze your prompts and select the optimal combination of
                    reasoning methods based on task complexity, available models, and domain requirements.
                  </p>
                </CardContent>
              </Card>
            ) : selectedMethods.length === 0 ? (
              <Card className="border-border bg-card border-dashed">
                <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                  <div className="rounded-full bg-muted p-4 mb-4">
                    <Brain className="h-8 w-8 text-muted-foreground" />
                  </div>
                  <h3 className="font-semibold text-lg mb-2">No Methods Selected</h3>
                  <p className="text-muted-foreground max-w-md">
                    Select one or more reasoning methods to customize how LLMHive thinks.
                  </p>
                </CardContent>
              </Card>
            ) : (
              <ScrollArea className="h-[calc(100vh-220px)]">
                <div className="grid gap-4 pr-4">
                  {selectedMethods.map((method) => (
                    <Card key={method.id} className="border-border bg-card hover-lift">
                      <CardHeader className="pb-3">
                        <div className="flex items-start justify-between gap-4">
                          <div className="flex-1 min-w-0">
                            <CardTitle className="text-base">{method.name}</CardTitle>
                            <Badge variant="secondary" className="mt-2">
                              {CATEGORY_ICONS[method.category]}
                              <span className="ml-1">{method.category}</span>
                            </Badge>
                          </div>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-muted-foreground hover:text-destructive"
                            onClick={() => removeMethod(method.id)}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <p className="text-sm text-muted-foreground">{method.shortDescription}</p>

                        <div className="grid gap-4 sm:grid-cols-2">
                          <div>
                            <h4 className="text-sm font-medium text-green-500 mb-2 flex items-center gap-1">
                              <Check className="h-3 w-3" />
                              Strengths
                            </h4>
                            <ul className="space-y-1">
                              {method.strengths.map((strength, i) => (
                                <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                                  <span className="text-green-500 mt-1">•</span>
                                  {strength}
                                </li>
                              ))}
                            </ul>
                          </div>
                          <div>
                            <h4 className="text-sm font-medium text-amber-500 mb-2 flex items-center gap-1">
                              <AlertCircle className="h-3 w-3" />
                              Weaknesses
                            </h4>
                            <ul className="space-y-1">
                              {method.weaknesses.map((weakness, i) => (
                                <li key={i} className="text-xs text-muted-foreground flex items-start gap-2">
                                  <span className="text-amber-500 mt-1">•</span>
                                  {weakness}
                                </li>
                              ))}
                            </ul>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </ScrollArea>
            )}
          </div>
        </div>
      </main>
    </div>
  )
}
