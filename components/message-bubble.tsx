"use client"

import { useState, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Copy, Check, ThumbsUp, ThumbsDown, RefreshCw, Maximize2, Code, Share2, Eye, EyeOff, Twitter, Link, MessageSquare, Info } from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { Message, Artifact } from "@/lib/types"
import { cn } from "@/lib/utils"
import { toast } from "@/lib/toast"
import { AnswerQualityDrawer, useDevMode, type QualityMetadata } from "@/components/answer-quality-drawer"

// Record feedback to backend for RLHF training
async function recordFeedback(
  feedbackType: "thumbs_up" | "thumbs_down" | "copy" | "share" | "regenerate",
  userQuery: string,
  answerText: string,
  modelUsed?: string,
  sessionId?: string,
) {
  try {
    await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_query: userQuery,
        answer_text: answerText,
        feedback_type: feedbackType,
        model_used: modelUsed,
        session_id: sessionId,
      }),
    })
  } catch (error) {
    // Silently fail - feedback is non-critical
    console.debug("[Feedback] Failed to record:", error)
  }
}

interface MessageBubbleProps {
  message: Message
  previousUserMessage?: Message // For context
  onShowArtifact: (artifact: Artifact) => void
  onShowInsights: () => void
  incognitoMode: boolean
  onToggleIncognito: () => void
  onRegenerate?: () => void
  conversationId?: string
}

export function MessageBubble({
  message,
  previousUserMessage,
  onShowArtifact,
  onShowInsights,
  incognitoMode,
  onToggleIncognito,
  onRegenerate,
  conversationId,
}: MessageBubbleProps) {
  const [copied, setCopied] = useState(false)
  const [liked, setLiked] = useState(false)
  const [disliked, setDisliked] = useState(false)
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [feedbackSent, setFeedbackSent] = useState(false)
  const isDevMode = useDevMode()
  
  // Get the user query that prompted this response
  const userQuery = previousUserMessage?.content || ""
  
  // Extract quality metadata from message if available
  const qualityMetadata: QualityMetadata | undefined = message.qualityMetadata ? {
    traceId: message.qualityMetadata.traceId,
    confidence: message.qualityMetadata.confidence,
    confidenceLabel: message.qualityMetadata.confidenceLabel,
    modelsUsed: message.qualityMetadata.modelsUsed,
    strategyUsed: message.qualityMetadata.strategyUsed,
    verificationStatus: message.qualityMetadata.verificationStatus,
    verificationScore: message.qualityMetadata.verificationScore,
    toolsUsed: message.qualityMetadata.toolsUsed,
    ragUsed: message.qualityMetadata.ragUsed,
    memoryUsed: message.qualityMetadata.memoryUsed,
    sources: message.qualityMetadata.sources,
    isStub: message.qualityMetadata.isStub,
    selfGraded: message.qualityMetadata.selfGraded,
    improvementApplied: message.qualityMetadata.improvementApplied,
  } : undefined

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(message.content)
    setCopied(true)
    toast.success("Copied to clipboard")
    setTimeout(() => setCopied(false), 2000)
    
    // Track copy as implicit positive feedback (non-blocking)
    if (userQuery) {
      recordFeedback("copy", userQuery, message.content, message.model, conversationId)
    }
  }, [message.content, message.model, userQuery, conversationId])

  const handleLike = useCallback(() => {
    const newLiked = !liked
    setLiked(newLiked)
    if (disliked) setDisliked(false)
    
    if (newLiked) {
      toast.success("Thanks for your feedback! 🎉")
      setFeedbackSent(true)
      
      // Record positive feedback for RLHF training
      if (userQuery) {
        recordFeedback("thumbs_up", userQuery, message.content, message.model, conversationId)
      }
    }
  }, [liked, disliked, userQuery, message.content, message.model, conversationId])

  const handleDislike = useCallback(() => {
    const newDisliked = !disliked
    setDisliked(newDisliked)
    if (liked) setLiked(false)
    
    if (newDisliked) {
      toast.info("Thanks for helping us improve! 🛠️")
      setFeedbackSent(true)
      
      // Record negative feedback for RLHF training
      if (userQuery) {
        recordFeedback("thumbs_down", userQuery, message.content, message.model, conversationId)
      }
    }
  }, [liked, disliked, userQuery, message.content, message.model, conversationId])
  
  const handleRegenerate = useCallback(() => {
    if (onRegenerate) {
      setIsRegenerating(true)
      onRegenerate()
      setTimeout(() => setIsRegenerating(false), 500)
      
      // Track regeneration as implicit negative feedback
      if (userQuery) {
        recordFeedback("regenerate", userQuery, message.content, message.model, conversationId)
      }
    } else {
      toast.info("Regeneration not available for this message")
    }
  }, [onRegenerate, userQuery, message.content, message.model, conversationId])
  
  const handleShare = useCallback(async (method: 'copy-link' | 'twitter') => {
    const text = message.content.slice(0, 280)
    
    if (method === 'copy-link') {
      // Create a shareable format
      const shareText = `LLMHive Response:\n\n${message.content}`
      await navigator.clipboard.writeText(shareText)
      toast.success("Response copied for sharing")
    } else if (method === 'twitter') {
      const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}%0A%0A—%20via%20LLMHive`
      window.open(twitterUrl, '_blank', 'width=550,height=420')
    }
    
    // Track share as positive feedback (user liked it enough to share)
    if (userQuery) {
      recordFeedback("share", userQuery, message.content, message.model, conversationId)
    }
  }, [message.content, userQuery, message.model, conversationId])

  if (message.role === "user") {
    return (
      <div className="flex gap-3 items-start justify-end">
        <div className="max-w-[80%] rounded-2xl bg-[var(--bronze)]/10 border border-[var(--bronze)]/20 p-4">
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
          {message.attachments && message.attachments.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {message.attachments.map((att) => (
                <div key={att.id} className="text-xs bg-secondary px-2 py-1 rounded">
                  {att.name}
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-muted to-muted-foreground/20 flex items-center justify-center flex-shrink-0">
          <span className="text-xs font-bold">U</span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex gap-3 items-start">
      <div className="flex flex-col gap-1">
        {message.agents && !incognitoMode ? (
          <div className="flex flex-wrap gap-1 w-8">
            {message.agents.slice(0, 4).map((agent) => (
              <div
                key={agent.agentId}
                className="w-3 h-3 rounded-sm bg-gradient-to-br from-[var(--bronze)] to-[var(--gold)] flex items-center justify-center"
                title={agent.agentName}
                style={{
                  clipPath: "polygon(30% 0%, 70% 0%, 100% 30%, 100% 70%, 70% 100%, 30% 100%, 0% 70%, 0% 30%)",
                }}
              />
            ))}
          </div>
        ) : (
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[var(--bronze)] to-[var(--gold)] flex items-center justify-center flex-shrink-0 glow-effect">
            <span className="text-xs font-bold text-background">AI</span>
          </div>
        )}
      </div>

      <div className="flex-1 max-w-[85%]">
        {message.consensus && (
          <div className="mb-2 inline-flex items-center gap-2 px-2 py-1 rounded-full bg-[var(--bronze)]/10 border border-[var(--bronze)]/20">
            <div
              className={cn(
                "w-2 h-2 rounded-full",
                message.consensus.confidence >= 80 ? "bg-green-500" : "bg-yellow-500",
              )}
            />
            <span className="text-xs text-[var(--bronze)] font-medium">{message.consensus.confidence}% consensus</span>
          </div>
        )}

        {message.reasoning && message.reasoning.mode === "deep" && (
          <div className="mb-3 p-3 rounded-lg bg-secondary/50 border border-border">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-5 h-5 rounded bg-[var(--bronze)]/20 flex items-center justify-center">
                <Code className="h-3 w-3 text-[var(--bronze)]" />
              </div>
              <span className="text-xs font-medium text-[var(--bronze)]">Deep Reasoning Mode</span>
            </div>
            {message.reasoning.steps && (
              <div className="space-y-1">
                {message.reasoning.steps.map((step, idx) => (
                  <div key={idx} className="text-xs text-muted-foreground flex items-start gap-2">
                    <span className="text-[var(--bronze)] font-medium">{idx + 1}.</span>
                    <span>{step}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="rounded-2xl bg-card border border-border p-4">
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>

          {message.citations && message.citations.length > 0 && (
            <div className="mt-3 pt-3 border-t border-border space-y-2">
              <p className="text-xs font-medium text-muted-foreground">Sources:</p>
              {message.citations.map((citation, idx) => (
                <div key={citation.id} className="text-xs flex items-start gap-2">
                  <span className="font-mono text-[var(--bronze)]">[{idx + 1}]</span>
                  <a
                    href={citation.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[var(--bronze)] hover:underline flex-1"
                  >
                    {citation.source}
                  </a>
                </div>
              ))}
            </div>
          )}

          {message.artifact && (
            <div className="mt-4 p-3 rounded-lg bg-secondary border border-border hover:border-[var(--bronze)] transition-colors">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-6 h-6 rounded bg-gradient-to-br from-[var(--bronze)] to-[var(--gold)] flex items-center justify-center">
                    <Code className="h-3 w-3 text-background" />
                  </div>
                  <span className="text-sm font-medium">{message.artifact.title}</span>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => onShowArtifact(message.artifact!)}
                  className="h-7 gap-1 hover:bg-[var(--bronze)]/10"
                >
                  <Maximize2 className="h-3 w-3" />
                  <span className="text-xs">Open</span>
                </Button>
              </div>
              <div className="text-xs text-muted-foreground">
                {message.artifact.type === "code" && `${message.artifact.language || "code"} artifact`}
                {message.artifact.type === "document" && "document artifact"}
                {message.artifact.type === "visualization" && "visualization artifact"}
              </div>
            </div>
          )}
        </div>
        
        {/* Why this answer? drawer - shows quality metadata */}
        {qualityMetadata && (
          <AnswerQualityDrawer 
            metadata={qualityMetadata} 
            isDevMode={isDevMode}
          />
        )}

        <div className="flex items-center gap-1 mt-2">
          <Button 
            size="icon" 
            variant="ghost" 
            className="h-7 w-7" 
            onClick={handleCopy}
            title="Copy response"
          >
            {copied ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3" />}
          </Button>
          <Button
            size="icon"
            variant="ghost"
            className={cn(
              "h-7 w-7 transition-all",
              liked && "text-[var(--bronze)] bg-[var(--bronze)]/10",
              feedbackSent && liked && "ring-1 ring-[var(--bronze)]/30"
            )}
            onClick={handleLike}
            title={liked ? "You liked this response" : "Good response"}
          >
            <ThumbsUp className={cn("h-3 w-3", liked && "fill-current")} />
          </Button>
          <Button
            size="icon"
            variant="ghost"
            className={cn(
              "h-7 w-7 transition-all",
              disliked && "text-destructive bg-destructive/10",
              feedbackSent && disliked && "ring-1 ring-destructive/30"
            )}
            onClick={handleDislike}
            title={disliked ? "You disliked this response" : "Poor response"}
          >
            <ThumbsDown className={cn("h-3 w-3", disliked && "fill-current")} />
          </Button>
          <Button 
            size="icon" 
            variant="ghost" 
            className={cn("h-7 w-7", isRegenerating && "animate-spin")}
            onClick={handleRegenerate}
            title="Regenerate response"
            disabled={isRegenerating}
          >
            <RefreshCw className="h-3 w-3" />
          </Button>
          
          {/* Share dropdown */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size="icon" variant="ghost" className="h-7 w-7" title="Share response">
            <Share2 className="h-3 w-3" />
          </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-40">
              <DropdownMenuItem onClick={() => handleShare('copy-link')} className="gap-2 cursor-pointer">
                <Link className="h-3 w-3" />
                <span className="text-xs">Copy to share</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleShare('twitter')} className="gap-2 cursor-pointer">
                <Twitter className="h-3 w-3" />
                <span className="text-xs">Share on X</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
          
          {message.agents && message.agents.length > 0 && (
            <Button size="sm" variant="ghost" className="h-7 gap-1 hover:text-[var(--bronze)]" onClick={onShowInsights}>
              <Eye className="h-3 w-3" />
              <span className="text-xs">Insights</span>
            </Button>
          )}
          <Button
            size="icon"
            variant="ghost"
            className={cn("h-7 w-7 ml-auto", !incognitoMode && "text-[var(--bronze)]")}
            onClick={onToggleIncognito}
            title={incognitoMode ? "Show agent contributions" : "Hide agent contributions"}
          >
            {incognitoMode ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
          </Button>
          {message.model && <span className="text-xs text-muted-foreground">{message.model}</span>}
        </div>
      </div>
    </div>
  )
}
