"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import { 
  Brain, 
  Zap, 
  Shield, 
  Layers, 
  ArrowRight, 
  X, 
  Sparkles,
  MessageSquare,
  Settings,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  Check,
  Building2,
} from "lucide-react"
import { useOnboarding } from "@/lib/hooks/use-onboarding"

interface OnboardingModalProps {
  userName?: string
}

const WELCOME_FEATURES = [
  {
    icon: Brain,
    title: "Multi-Model Intelligence",
    description: "GPT-4, Claude, Gemini, and more working together for superior results",
    color: "text-purple-400",
  },
  {
    icon: Zap,
    title: "ELITE Orchestration",
    description: "Advanced reasoning with HRM, DeepConf, and adaptive ensemble methods",
    color: "text-yellow-400",
  },
  {
    icon: Shield,
    title: "Enterprise Security",
    description: "PII redaction, content filtering, and comprehensive guardrails",
    color: "text-blue-400",
  },
  {
    icon: Layers,
    title: "Customizable Accuracy",
    description: "Choose from Standard to Maximum accuracy levels for your needs",
    color: "text-green-400",
  },
]

const TOUR_STEPS = [
  {
    title: "Start a Conversation",
    description: "Click 'New Chat' or use the text input to begin. LLMHive will automatically orchestrate the best models for your query.",
    icon: MessageSquare,
    highlight: "chat-input",
  },
  {
    title: "Customize Orchestration",
    description: "Access the Orchestration panel to choose accuracy levels, enable ELITE mode, and configure reasoning strategies.",
    icon: Settings,
    highlight: "orchestration-panel",
  },
  {
    title: "Explore Templates",
    description: "Use pre-built templates for research, coding, business analysis, and more. Each template is optimized for its use case.",
    icon: Sparkles,
    highlight: "templates",
  },
  {
    title: "Track Your Usage",
    description: "Monitor your query usage, view analytics, and manage your subscription from the billing page.",
    icon: BarChart3,
    highlight: "billing",
  },
  {
    title: "Run Business Ops",
    description: "Access security, billing, org management, and integrations from the Business Ops hub.",
    icon: Building2,
    highlight: "business-ops",
  },
]

export function OnboardingModal({ userName = "there" }: OnboardingModalProps) {
  const {
    shouldShowWelcome,
    shouldShowTour,
    state,
    startTour,
    nextStep,
    prevStep,
    completeTour,
    skipTour,
  } = useOnboarding()

  const [isVisible, setIsVisible] = useState(false)
  const [isAnimating, setIsAnimating] = useState(false)

  // Animate in on mount
  useEffect(() => {
    if (shouldShowWelcome || shouldShowTour) {
      setIsAnimating(true)
      const timer = setTimeout(() => {
        setIsVisible(true)
        setIsAnimating(false)
      }, 50)
      return () => clearTimeout(timer)
    }
  }, [shouldShowWelcome, shouldShowTour])

  // Don't render if nothing to show
  if (!shouldShowWelcome && !shouldShowTour) {
    return null
  }

  const firstName = userName.split(" ")[0]

  // Welcome Modal
  if (shouldShowWelcome) {
    return (
      <div 
        className={`fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 transition-opacity duration-300 ${
          isVisible ? "opacity-100" : "opacity-0"
        }`}
      >
        <div 
          className={`relative w-full max-w-2xl bg-[#171717] rounded-2xl border border-[#262626] shadow-2xl overflow-hidden transform transition-all duration-300 ${
            isVisible ? "scale-100 translate-y-0" : "scale-95 translate-y-4"
          }`}
        >
          {/* Close button */}
          <button
            onClick={skipTour}
            className="absolute top-4 right-4 text-muted-foreground hover:text-foreground transition-colors z-10"
            aria-label="Close"
          >
            <X className="h-5 w-5" />
          </button>

          {/* Header gradient */}
          <div className="relative h-32 bg-gradient-to-br from-[#C48E48] via-[#A67C3D] to-[#8B6914] overflow-hidden">
            <div className="absolute inset-0 opacity-30">
              <div className="absolute top-4 left-8 w-20 h-20 rounded-full bg-white/10 blur-xl" />
              <div className="absolute bottom-2 right-12 w-32 h-32 rounded-full bg-white/10 blur-2xl" />
            </div>
            <div className="relative h-full flex items-center justify-center">
              <div className="text-center">
                <h1 className="text-3xl font-bold text-[#0a0a0a]">
                  Welcome to LLMHive 🐝
                </h1>
                <p className="text-[#0a0a0a]/80 mt-1">
                  Elite Multi-Model AI Orchestration
                </p>
              </div>
            </div>
          </div>

          {/* Content */}
          <div className="p-8">
            <div>
              <h2 className="text-2xl font-semibold text-foreground mb-2">
                Hi {firstName}! 👋
              </h2>
              <p className="text-muted-foreground mb-6">
                You've just unlocked access to the most powerful AI orchestration platform. 
                Here's what makes LLMHive special:
              </p>
            </div>

            {/* Features grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
              {WELCOME_FEATURES.map((feature, index) => (
                <div
                  key={feature.title}
                  className="flex gap-3 p-4 rounded-xl bg-[#262626]/50 border border-[#333] animate-fade-in"
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  <div className={`flex-shrink-0 ${feature.color}`}>
                    <feature.icon className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="font-medium text-foreground text-sm">
                      {feature.title}
                    </h3>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {feature.description}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {/* Actions */}
            <div className="flex flex-col sm:flex-row gap-3">
              <Button
                onClick={startTour}
                className="flex-1 bronze-gradient text-[#0a0a0a] font-semibold"
              >
                Take a Quick Tour
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
              <Link href="/business-ops" className="flex-1">
                <Button variant="outline" className="w-full">
                  Business Ops Hub
                </Button>
              </Link>
              <Button
                onClick={skipTour}
                variant="outline"
                className="flex-1"
              >
                Skip for Now
              </Button>
            </div>

            <p className="text-xs text-center text-muted-foreground mt-4">
              You can always access the tour from Settings → Help
            </p>
          </div>
        </div>
      </div>
    )
  }

  // Feature Tour
  if (shouldShowTour) {
    const currentStepIndex = state.currentStep - 1
    const step = TOUR_STEPS[currentStepIndex]
    const isLastStep = currentStepIndex === TOUR_STEPS.length - 1
    const isFirstStep = currentStepIndex === 0

    if (!step) {
      completeTour()
      return null
    }

    return (
      <div 
        className={`fixed inset-0 z-50 pointer-events-none transition-opacity duration-300 ${
          isVisible ? "opacity-100" : "opacity-0"
        }`}
      >
        {/* Overlay */}
        <div 
          className="absolute inset-0 bg-black/40 pointer-events-auto" 
          onClick={skipTour} 
        />

        {/* Tour card */}
        <div 
          className={`absolute bottom-8 left-1/2 -translate-x-1/2 w-full max-w-md px-4 pointer-events-auto transform transition-all duration-300 ${
            isVisible ? "translate-y-0" : "translate-y-12"
          }`}
        >
          <div className="bg-[#171717] rounded-xl border border-[#262626] shadow-2xl overflow-hidden">
            {/* Progress bar */}
            <div className="h-1 bg-[#262626]">
              <div
                className="h-full bg-[#C48E48] transition-all duration-300"
                style={{ width: `${((currentStepIndex + 1) / TOUR_STEPS.length) * 100}%` }}
              />
            </div>

            <div className="p-6">
              {/* Step indicator */}
              <div className="flex items-center gap-2 mb-4">
                <span className="text-xs text-muted-foreground">
                  Step {currentStepIndex + 1} of {TOUR_STEPS.length}
                </span>
                <div className="flex gap-1 ml-auto">
                  {TOUR_STEPS.map((_, i) => (
                    <div
                      key={i}
                      className={`w-2 h-2 rounded-full transition-colors ${
                        i <= currentStepIndex ? "bg-[#C48E48]" : "bg-[#333]"
                      }`}
                    />
                  ))}
                </div>
              </div>

              {/* Content */}
              <div className="flex gap-4">
                <div className="flex-shrink-0 w-12 h-12 rounded-xl bg-[#C48E48]/10 flex items-center justify-center">
                  <step.icon className="h-6 w-6 text-[#C48E48]" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-foreground mb-1">
                    {step.title}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {step.description}
                  </p>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 mt-6">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={skipTour}
                  className="text-muted-foreground"
                >
                  Skip Tour
                </Button>
                
                <div className="flex-1" />

                {!isFirstStep && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={prevStep}
                  >
                    <ChevronLeft className="h-4 w-4 mr-1" />
                    Back
                  </Button>
                )}

                <Button
                  size="sm"
                  onClick={isLastStep ? completeTour : nextStep}
                  className="bronze-gradient text-[#0a0a0a]"
                >
                  {isLastStep ? (
                    <>
                      <Check className="h-4 w-4 mr-1" />
                      Done
                    </>
                  ) : (
                    <>
                      Next
                      <ChevronRight className="h-4 w-4 ml-1" />
                    </>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return null
}
