"use client"

/**
 * Prompt Playground Component
 * 
 * Interactive prompt builder and testing area with:
 * - Model selection
 * - Guided prompt building (simple mode)
 * - Advanced parameter controls
 * - Streaming output
 * - Template saving
 * - Cost estimation
 */

import * as React from "react"
import { 
  Play, 
  Settings, 
  Save, 
  Copy, 
  RotateCcw, 
  Loader2, 
  Sparkles,
  ChevronDown,
  Wand2,
  FileText,
  Sliders,
  DollarSign,
  Clock,
  Check,
  AlertCircle,
  MessageSquare,
  Send,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { toast } from "sonner"

import type { OpenRouterModel, ChatMessage, ChatCompletionResponse, PromptTemplate } from "@/lib/openrouter/types"
import { formatPrice, formatContextLength } from "@/lib/openrouter/types"
import { chatCompletion, streamChatCompletion, estimateTokens, estimateCost, createTemplate } from "@/lib/openrouter/api"

// =============================================================================
// Types
// =============================================================================

interface PlaygroundState {
  mode: 'simple' | 'advanced'
  systemPrompt: string
  userPrompt: string
  
  // Simple mode fields
  task: string
  context: string
  format: string
  tone: string
  constraints: string
  
  // Advanced mode
  messages: ChatMessage[]
  
  // Parameters
  temperature: number
  maxTokens: number
  topP: number
  
  // State
  running: boolean
  response: string
  responseMetadata: {
    latencyMs?: number
    promptTokens?: number
    completionTokens?: number
    costUsd?: number
    model?: string
  } | null
  error: string | null
}

interface PromptPlaygroundProps {
  selectedModel?: OpenRouterModel
  onChangeModel?: () => void
  userId?: string
}

// =============================================================================
// Simple Mode Builder Component
// =============================================================================

interface SimpleModeBuilderProps {
  state: PlaygroundState
  onChange: (updates: Partial<PlaygroundState>) => void
}

function SimpleModeBuilder({ state, onChange }: SimpleModeBuilderProps) {
  const toneOptions = [
    { value: 'professional', label: 'Professional' },
    { value: 'casual', label: 'Casual & Friendly' },
    { value: 'formal', label: 'Formal' },
    { value: 'creative', label: 'Creative' },
    { value: 'technical', label: 'Technical' },
    { value: 'simple', label: 'Simple & Clear' },
  ]
  
  const formatOptions = [
    { value: 'paragraph', label: 'Paragraph' },
    { value: 'bullet', label: 'Bullet Points' },
    { value: 'numbered', label: 'Numbered List' },
    { value: 'table', label: 'Table' },
    { value: 'json', label: 'JSON' },
    { value: 'code', label: 'Code' },
  ]
  
  // Build prompt from simple mode fields
  React.useEffect(() => {
    const parts = []
    
    if (state.context) {
      parts.push(`Context: ${state.context}`)
    }
    if (state.task) {
      parts.push(`Task: ${state.task}`)
    }
    if (state.format && state.format !== 'paragraph') {
      parts.push(`Format the response as: ${state.format}`)
    }
    if (state.constraints) {
      parts.push(`Constraints: ${state.constraints}`)
    }
    
    const systemParts = []
    if (state.tone) {
      const toneLabel = toneOptions.find(t => t.value === state.tone)?.label
      systemParts.push(`Use a ${toneLabel?.toLowerCase()} tone.`)
    }
    
    onChange({
      userPrompt: parts.join('\n\n'),
      systemPrompt: systemParts.join(' '),
    })
  }, [state.task, state.context, state.format, state.tone, state.constraints])
  
  return (
    <div className="space-y-6">
      {/* Task */}
      <div className="space-y-2">
        <Label htmlFor="task" className="text-base font-medium">
          What do you want to do?
        </Label>
        <p className="text-sm text-muted-foreground">
          Describe what you want the AI to help with
        </p>
        <Textarea
          id="task"
          placeholder="e.g., Summarize this article, Write a product description, Explain this concept..."
          value={state.task}
          onChange={(e) => onChange({ task: e.target.value })}
          rows={3}
          className="resize-none"
        />
      </div>
      
      {/* Context */}
      <div className="space-y-2">
        <Label htmlFor="context" className="text-base font-medium">
          What should the AI know?
        </Label>
        <p className="text-sm text-muted-foreground">
          Provide any background information, content to work with, or specific details
        </p>
        <Textarea
          id="context"
          placeholder="Paste the text to summarize, describe your product, explain the topic..."
          value={state.context}
          onChange={(e) => onChange({ context: e.target.value })}
          rows={5}
          className="resize-none"
        />
      </div>
      
      {/* Format & Tone */}
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label className="text-base font-medium">Output Format</Label>
          <Select
            value={state.format}
            onValueChange={(v) => onChange({ format: v })}
          >
            <SelectTrigger>
              <SelectValue placeholder="Choose format" />
            </SelectTrigger>
            <SelectContent>
              {formatOptions.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        
        <div className="space-y-2">
          <Label className="text-base font-medium">Tone</Label>
          <Select
            value={state.tone}
            onValueChange={(v) => onChange({ tone: v })}
          >
            <SelectTrigger>
              <SelectValue placeholder="Choose tone" />
            </SelectTrigger>
            <SelectContent>
              {toneOptions.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      
      {/* Constraints */}
      <Collapsible>
        <CollapsibleTrigger asChild>
          <Button variant="ghost" className="gap-2 p-0 h-auto font-medium">
            <ChevronDown className="w-4 h-4" />
            Additional Constraints (optional)
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-2">
          <Textarea
            placeholder="e.g., Keep it under 100 words, Include specific keywords, Avoid technical jargon..."
            value={state.constraints}
            onChange={(e) => onChange({ constraints: e.target.value })}
            rows={2}
            className="resize-none"
          />
        </CollapsibleContent>
      </Collapsible>
    </div>
  )
}

// =============================================================================
// Advanced Mode Builder Component
// =============================================================================

interface AdvancedModeBuilderProps {
  state: PlaygroundState
  onChange: (updates: Partial<PlaygroundState>) => void
}

function AdvancedModeBuilder({ state, onChange }: AdvancedModeBuilderProps) {
  return (
    <div className="space-y-4">
      {/* System Prompt */}
      <div className="space-y-2">
        <Label htmlFor="system" className="font-medium">
          System Instructions
        </Label>
        <Textarea
          id="system"
          placeholder="You are a helpful assistant..."
          value={state.systemPrompt}
          onChange={(e) => onChange({ systemPrompt: e.target.value })}
          rows={3}
          className="resize-none font-mono text-sm"
        />
      </div>
      
      {/* User Prompt */}
      <div className="space-y-2">
        <Label htmlFor="user" className="font-medium">
          User Message
        </Label>
        <Textarea
          id="user"
          placeholder="Enter your prompt..."
          value={state.userPrompt}
          onChange={(e) => onChange({ userPrompt: e.target.value })}
          rows={8}
          className="resize-none font-mono text-sm"
        />
      </div>
    </div>
  )
}

// =============================================================================
// Parameters Panel Component
// =============================================================================

interface ParametersPanelProps {
  state: PlaygroundState
  onChange: (updates: Partial<PlaygroundState>) => void
  model?: OpenRouterModel
}

function ParametersPanel({ state, onChange, model }: ParametersPanelProps) {
  return (
    <div className="space-y-6">
      {/* Temperature */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label className="font-medium">Creativity</Label>
          <span className="text-sm text-muted-foreground">
            {state.temperature.toFixed(1)}
          </span>
        </div>
        <Slider
          value={[state.temperature]}
          onValueChange={([v]) => onChange({ temperature: v })}
          max={2}
          min={0}
          step={0.1}
        />
        <p className="text-xs text-muted-foreground">
          {state.temperature < 0.3 ? "Focused & consistent" :
           state.temperature < 0.7 ? "Balanced" :
           state.temperature < 1.2 ? "Creative" :
           "Very creative (may be unpredictable)"}
        </p>
      </div>
      
      {/* Max Tokens */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <Label className="font-medium">Response Length</Label>
          <span className="text-sm text-muted-foreground">
            {state.maxTokens} tokens (~{Math.round(state.maxTokens * 4)} chars)
          </span>
        </div>
        <Slider
          value={[state.maxTokens]}
          onValueChange={([v]) => onChange({ maxTokens: v })}
          max={model?.top_provider_max_tokens || 4096}
          min={50}
          step={50}
        />
        <p className="text-xs text-muted-foreground">
          {state.maxTokens < 500 ? "Short response" :
           state.maxTokens < 1500 ? "Medium response" :
           "Long response"}
        </p>
      </div>
      
      {/* Top P (advanced) */}
      <Collapsible>
        <CollapsibleTrigger asChild>
          <Button variant="ghost" size="sm" className="gap-2 p-0 h-auto text-sm">
            <ChevronDown className="w-3 h-3" />
            Advanced Parameters
          </Button>
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-4 space-y-4">
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="text-sm">Top P</Label>
              <span className="text-xs text-muted-foreground">
                {state.topP.toFixed(2)}
              </span>
            </div>
            <Slider
              value={[state.topP]}
              onValueChange={([v]) => onChange({ topP: v })}
              max={1}
              min={0}
              step={0.05}
            />
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  )
}

// =============================================================================
// Main Component
// =============================================================================

export function PromptPlayground({
  selectedModel,
  onChangeModel,
  userId,
}: PromptPlaygroundProps) {
  const [state, setState] = React.useState<PlaygroundState>({
    mode: 'simple',
    systemPrompt: '',
    userPrompt: '',
    task: '',
    context: '',
    format: 'paragraph',
    tone: 'professional',
    constraints: '',
    messages: [],
    temperature: 0.7,
    maxTokens: 1024,
    topP: 1,
    running: false,
    response: '',
    responseMetadata: null,
    error: null,
  })
  
  const [showSaveDialog, setShowSaveDialog] = React.useState(false)
  const [templateName, setTemplateName] = React.useState('')
  
  const updateState = (updates: Partial<PlaygroundState>) => {
    setState((prev) => ({ ...prev, ...updates }))
  }
  
  // Estimate cost
  const estimatedPromptTokens = estimateTokens(
    state.systemPrompt + state.userPrompt + state.context + state.task
  )
  const estimatedCost = selectedModel
    ? estimateCost(selectedModel, estimatedPromptTokens, state.maxTokens)
    : 0
  
  // Run prompt
  const handleRun = async () => {
    if (!selectedModel) {
      toast.error("Please select a model first")
      return
    }
    
    if (!state.userPrompt && !state.task) {
      toast.error("Please enter a prompt")
      return
    }
    
    updateState({ running: true, response: '', error: null, responseMetadata: null })
    const startTime = Date.now()
    
    try {
      const messages: ChatMessage[] = []
      
      if (state.systemPrompt) {
        messages.push({ role: 'system', content: state.systemPrompt })
      }
      
      messages.push({ role: 'user', content: state.userPrompt || state.task })
      
      // Stream response
      let fullResponse = ''
      let usage: { prompt_tokens?: number; completion_tokens?: number } = {}
      
      for await (const chunk of streamChatCompletion({
        model: selectedModel.id,
        messages,
        temperature: state.temperature,
        max_tokens: state.maxTokens,
        top_p: state.topP,
      })) {
        const delta = chunk.choices[0]?.delta?.content
        if (delta) {
          fullResponse += delta
          updateState({ response: fullResponse })
        }
        if (chunk.usage) {
          usage = chunk.usage
        }
      }
      
      const latencyMs = Date.now() - startTime
      const cost = estimateCost(
        selectedModel,
        usage.prompt_tokens || estimatedPromptTokens,
        usage.completion_tokens || estimateTokens(fullResponse)
      )
      
      updateState({
        running: false,
        responseMetadata: {
          latencyMs,
          promptTokens: usage.prompt_tokens,
          completionTokens: usage.completion_tokens,
          costUsd: cost,
          model: selectedModel.name,
        },
      })
      
    } catch (e) {
      updateState({
        running: false,
        error: e instanceof Error ? e.message : "An error occurred",
      })
    }
  }
  
  // Copy response
  const handleCopy = () => {
    navigator.clipboard.writeText(state.response)
    toast.success("Copied to clipboard")
  }
  
  // Save as template
  const handleSaveTemplate = async () => {
    if (!userId || !templateName) return
    
    try {
      await createTemplate(userId, {
        name: templateName,
        system_prompt: state.systemPrompt,
        user_prompt_template: state.userPrompt || `Task: {{task}}\n\nContext: {{context}}`,
        default_model_id: selectedModel?.id,
        default_params: {
          temperature: state.temperature,
          max_tokens: state.maxTokens,
        },
      })
      
      toast.success("Template saved!")
      setShowSaveDialog(false)
      setTemplateName('')
    } catch (e) {
      toast.error("Failed to save template")
    }
  }
  
  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b bg-background">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div>
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Wand2 className="w-5 h-5" />
                Prompt Playground
              </h2>
              <p className="text-sm text-muted-foreground">
                Build and test prompts with any model
              </p>
            </div>
          </div>
          
          {/* Model selector */}
          <div className="flex items-center gap-3">
            {selectedModel ? (
              <Button variant="outline" onClick={onChangeModel} className="gap-2">
                <Sparkles className="w-4 h-4" />
                {selectedModel.name}
                <ChevronDown className="w-4 h-4" />
              </Button>
            ) : (
              <Button onClick={onChangeModel}>
                Select Model
              </Button>
            )}
          </div>
        </div>
      </div>
      
      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left: Prompt Builder */}
        <div className="flex-1 flex flex-col border-r overflow-hidden">
          <Tabs
            value={state.mode}
            onValueChange={(v) => updateState({ mode: v as 'simple' | 'advanced' })}
            className="flex-1 flex flex-col"
          >
            <div className="px-4 pt-4 flex items-center justify-between">
              <TabsList>
                <TabsTrigger value="simple" className="gap-2">
                  <Sparkles className="w-4 h-4" />
                  Simple
                </TabsTrigger>
                <TabsTrigger value="advanced" className="gap-2">
                  <FileText className="w-4 h-4" />
                  Advanced
                </TabsTrigger>
              </TabsList>
              
              {/* Cost estimate hidden from customer view */}
            </div>
            
            <ScrollArea className="flex-1">
              <div className="p-4">
                <TabsContent value="simple" className="mt-0">
                  <SimpleModeBuilder state={state} onChange={updateState} />
                </TabsContent>
                
                <TabsContent value="advanced" className="mt-0">
                  <AdvancedModeBuilder state={state} onChange={updateState} />
                </TabsContent>
              </div>
            </ScrollArea>
            
            {/* Run button */}
            <div className="p-4 border-t bg-background">
              <div className="flex items-center gap-2">
                <Button
                  onClick={handleRun}
                  disabled={state.running || !selectedModel}
                  className="flex-1 gap-2"
                >
                  {state.running ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Running...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" />
                      Run
                    </>
                  )}
                </Button>
                
                <Dialog open={showSaveDialog} onOpenChange={setShowSaveDialog}>
                  <DialogTrigger asChild>
                    <Button variant="outline" size="icon">
                      <Save className="w-4 h-4" />
                    </Button>
                  </DialogTrigger>
                  <DialogContent>
                    <DialogHeader>
                      <DialogTitle>Save as Template</DialogTitle>
                      <DialogDescription>
                        Save this prompt configuration as a reusable template
                      </DialogDescription>
                    </DialogHeader>
                    <div className="py-4">
                      <Label htmlFor="templateName">Template Name</Label>
                      <Input
                        id="templateName"
                        value={templateName}
                        onChange={(e) => setTemplateName(e.target.value)}
                        placeholder="My Prompt Template"
                        className="mt-2"
                      />
                    </div>
                    <DialogFooter>
                      <Button variant="outline" onClick={() => setShowSaveDialog(false)}>
                        Cancel
                      </Button>
                      <Button onClick={handleSaveTemplate} disabled={!templateName}>
                        Save Template
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>
            </div>
          </Tabs>
        </div>
        
        {/* Right: Parameters + Response */}
        <div className="w-96 flex flex-col overflow-hidden bg-muted/30">
          {/* Parameters */}
          <Collapsible defaultOpen>
            <CollapsibleTrigger asChild>
              <div className="p-4 border-b flex items-center justify-between cursor-pointer hover:bg-muted/50">
                <h3 className="font-semibold flex items-center gap-2">
                  <Sliders className="w-4 h-4" />
                  Parameters
                </h3>
                <ChevronDown className="w-4 h-4" />
              </div>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="p-4 border-b">
                <ParametersPanel
                  state={state}
                  onChange={updateState}
                  model={selectedModel}
                />
              </div>
            </CollapsibleContent>
          </Collapsible>
          
          {/* Response */}
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="p-4 border-b flex items-center justify-between">
              <h3 className="font-semibold flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                Response
              </h3>
              
              {state.response && (
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="sm" onClick={handleCopy}>
                    <Copy className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => updateState({ response: '', responseMetadata: null })}
                  >
                    <RotateCcw className="w-4 h-4" />
                  </Button>
                </div>
              )}
            </div>
            
            <ScrollArea className="flex-1">
              <div className="p-4">
                {state.error ? (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{state.error}</AlertDescription>
                  </Alert>
                ) : state.running ? (
                  <div className="space-y-4">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Generating response...
                    </div>
                    {state.response && (
                      <div className="prose prose-sm dark:prose-invert max-w-none">
                        {state.response}
                        <span className="animate-pulse">▊</span>
                      </div>
                    )}
                  </div>
                ) : state.response ? (
                  <div className="space-y-4">
                    <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap">
                      {state.response}
                    </div>
                    
                    {state.responseMetadata && (
                      <div className="flex flex-wrap gap-2 pt-4 border-t">
                        <Badge variant="secondary" className="gap-1">
                          <Clock className="w-3 h-3" />
                          {(state.responseMetadata.latencyMs || 0) / 1000}s
                        </Badge>
                        {state.responseMetadata.promptTokens && (
                          <Badge variant="secondary">
                            {state.responseMetadata.promptTokens} → {state.responseMetadata.completionTokens} tokens
                          </Badge>
                        )}
                        {/* Cost hidden from customer view */}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-center text-muted-foreground py-8">
                    <Send className="w-8 h-8 mx-auto mb-3 opacity-50" />
                    <p>Run a prompt to see the response</p>
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>
        </div>
      </div>
    </div>
  )
}

export default PromptPlayground

