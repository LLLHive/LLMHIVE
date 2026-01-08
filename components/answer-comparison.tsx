"use client"

import { useState, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Check, X, Equal, ChevronDown, ChevronUp, Sparkles } from "lucide-react"
import { cn } from "@/lib/utils"
import { toast } from "@/lib/toast"

interface ComparisonAnswer {
  id: string
  content: string
  model: string
  latencyMs?: number
}

interface AnswerComparisonProps {
  query: string
  answerA: ComparisonAnswer
  answerB: ComparisonAnswer
  onPreferenceSelected: (preference: "A" | "B" | "tie", reason?: string) => void
  onSkip?: () => void
  showModelNames?: boolean
  conversationId?: string
}

// Record preference to backend for RLHF training
async function recordPreference(
  query: string,
  answerA: ComparisonAnswer,
  answerB: ComparisonAnswer,
  preference: "A" | "B" | "tie",
  reason?: string,
  conversationId?: string,
) {
  try {
    await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_query: query,
        answer_text: preference === "A" ? answerA.content : answerB.content,
        feedback_type: "preference",
        rating: preference === "tie" ? 0.5 : 1.0,
        model_used: preference === "A" ? answerA.model : answerB.model,
        session_id: conversationId,
        metadata: {
          comparison: true,
          answer_a_id: answerA.id,
          answer_b_id: answerB.id,
          answer_a_model: answerA.model,
          answer_b_model: answerB.model,
          preference,
          reason,
          rejected_model: preference === "A" ? answerB.model : preference === "B" ? answerA.model : null,
        },
      }),
    })
  } catch (error) {
    console.debug("[Comparison] Failed to record preference:", error)
  }
}

export function AnswerComparison({
  query,
  answerA,
  answerB,
  onPreferenceSelected,
  onSkip,
  showModelNames = false,
  conversationId,
}: AnswerComparisonProps) {
  const [selectedPreference, setSelectedPreference] = useState<"A" | "B" | "tie" | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [expandedAnswer, setExpandedAnswer] = useState<"A" | "B" | null>(null)
  const [showReasonInput, setShowReasonInput] = useState(false)
  const [reason, setReason] = useState("")

  const handleSelect = useCallback(async (preference: "A" | "B" | "tie") => {
    setSelectedPreference(preference)
    setIsSubmitting(true)

    try {
      // Record preference for RLHF training
      await recordPreference(query, answerA, answerB, preference, reason, conversationId)
      
      toast.success(
        preference === "tie" 
          ? "Thanks! Both answers noted as equal quality." 
          : `Thanks! Answer ${preference} selected as better.`
      )
      
      onPreferenceSelected(preference, reason)
    } catch (error) {
      console.error("[Comparison] Error:", error)
    } finally {
      setIsSubmitting(false)
    }
  }, [query, answerA, answerB, reason, conversationId, onPreferenceSelected])

  const toggleExpand = (answer: "A" | "B") => {
    setExpandedAnswer(expandedAnswer === answer ? null : answer)
  }

  const truncateText = (text: string, maxLength: number = 300) => {
    if (text.length <= maxLength) return text
    return text.slice(0, maxLength) + "..."
  }

  return (
    <div className="w-full max-w-4xl mx-auto space-y-4 p-4">
      {/* Header */}
      <div className="text-center space-y-2">
        <div className="flex items-center justify-center gap-2">
          <Sparkles className="h-5 w-5 text-[var(--bronze)]" />
          <h3 className="text-lg font-semibold">Which answer is better?</h3>
        </div>
        <p className="text-sm text-muted-foreground">
          Your choice helps us improve answer quality
        </p>
      </div>

      {/* Query Display */}
      <div className="p-3 rounded-lg bg-muted/50 border border-border">
        <p className="text-sm font-medium text-muted-foreground">Question:</p>
        <p className="text-sm mt-1">{query}</p>
      </div>

      {/* Answer Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Answer A */}
        <Card 
          className={cn(
            "cursor-pointer transition-all hover:border-[var(--bronze)]/50",
            selectedPreference === "A" && "border-[var(--bronze)] ring-2 ring-[var(--bronze)]/20 bg-[var(--bronze)]/5"
          )}
          onClick={() => !isSubmitting && handleSelect("A")}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <Badge variant="outline" className="text-xs">
                Answer A
              </Badge>
              {showModelNames && (
                <Badge variant="secondary" className="text-xs">
                  {answerA.model}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm leading-relaxed whitespace-pre-wrap">
              {expandedAnswer === "A" ? answerA.content : truncateText(answerA.content)}
            </p>
            {answerA.content.length > 300 && (
              <Button
                variant="ghost"
                size="sm"
                className="text-xs h-6 px-2"
                onClick={(e) => {
                  e.stopPropagation()
                  toggleExpand("A")
                }}
              >
                {expandedAnswer === "A" ? (
                  <>
                    <ChevronUp className="h-3 w-3 mr-1" />
                    Show less
                  </>
                ) : (
                  <>
                    <ChevronDown className="h-3 w-3 mr-1" />
                    Show more
                  </>
                )}
              </Button>
            )}
            {selectedPreference === "A" && (
              <div className="flex items-center gap-1 text-[var(--bronze)] text-sm font-medium">
                <Check className="h-4 w-4" />
                Selected as better
              </div>
            )}
          </CardContent>
        </Card>

        {/* Answer B */}
        <Card 
          className={cn(
            "cursor-pointer transition-all hover:border-[var(--bronze)]/50",
            selectedPreference === "B" && "border-[var(--bronze)] ring-2 ring-[var(--bronze)]/20 bg-[var(--bronze)]/5"
          )}
          onClick={() => !isSubmitting && handleSelect("B")}
        >
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <Badge variant="outline" className="text-xs">
                Answer B
              </Badge>
              {showModelNames && (
                <Badge variant="secondary" className="text-xs">
                  {answerB.model}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            <p className="text-sm leading-relaxed whitespace-pre-wrap">
              {expandedAnswer === "B" ? answerB.content : truncateText(answerB.content)}
            </p>
            {answerB.content.length > 300 && (
              <Button
                variant="ghost"
                size="sm"
                className="text-xs h-6 px-2"
                onClick={(e) => {
                  e.stopPropagation()
                  toggleExpand("B")
                }}
              >
                {expandedAnswer === "B" ? (
                  <>
                    <ChevronUp className="h-3 w-3 mr-1" />
                    Show less
                  </>
                ) : (
                  <>
                    <ChevronDown className="h-3 w-3 mr-1" />
                    Show more
                  </>
                )}
              </Button>
            )}
            {selectedPreference === "B" && (
              <div className="flex items-center gap-1 text-[var(--bronze)] text-sm font-medium">
                <Check className="h-4 w-4" />
                Selected as better
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-center gap-3">
        <Button
          variant="outline"
          size="sm"
          onClick={() => handleSelect("tie")}
          disabled={isSubmitting}
          className={cn(
            "gap-2",
            selectedPreference === "tie" && "border-[var(--bronze)] bg-[var(--bronze)]/10"
          )}
        >
          <Equal className="h-4 w-4" />
          Both are equal
        </Button>
        
        {onSkip && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onSkip}
            disabled={isSubmitting}
            className="gap-2 text-muted-foreground"
          >
            <X className="h-4 w-4" />
            Skip
          </Button>
        )}
      </div>

      {/* Optional Reason Input */}
      {selectedPreference && !isSubmitting && (
        <div className="text-center">
          {!showReasonInput ? (
            <Button
              variant="link"
              size="sm"
              onClick={() => setShowReasonInput(true)}
              className="text-xs text-muted-foreground"
            >
              Add a reason (optional)
            </Button>
          ) : (
            <div className="space-y-2 max-w-md mx-auto">
              <input
                type="text"
                placeholder="Why is this answer better?"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg border border-border bg-background focus:border-[var(--bronze)] focus:outline-none"
              />
              <p className="text-xs text-muted-foreground">
                Your feedback helps train our models
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Hook to trigger answer comparison for A/B testing
 */
export function useAnswerComparison() {
  const [comparisonData, setComparisonData] = useState<{
    query: string
    answerA: ComparisonAnswer
    answerB: ComparisonAnswer
  } | null>(null)

  const showComparison = useCallback((
    query: string,
    answerA: ComparisonAnswer,
    answerB: ComparisonAnswer,
  ) => {
    setComparisonData({ query, answerA, answerB })
  }, [])

  const hideComparison = useCallback(() => {
    setComparisonData(null)
  }, [])

  return {
    comparisonData,
    showComparison,
    hideComparison,
    isComparing: comparisonData !== null,
  }
}

