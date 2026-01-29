"use client"

import Link from "next/link"
import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { 
  ArrowLeft, 
  Search,
  ChevronDown,
  ChevronUp,
  Zap,
  CreditCard,
  Shield,
  Settings,
  MessageSquare,
  BookOpen,
  ExternalLink,
  HelpCircle,
  ArrowRight
} from "lucide-react"

interface FAQItem {
  question: string
  answer: string
}

interface FAQCategory {
  id: string
  name: string
  icon: React.ReactNode
  faqs: FAQItem[]
}

const faqCategories: FAQCategory[] = [
  {
    id: "getting-started",
    name: "Getting Started",
    icon: <Zap className="h-5 w-5" />,
    faqs: [
      {
        question: "What is LLMHive?",
        answer: "LLMHive is an AI orchestration platform that dynamically routes your queries to the best-performing AI models across all major providers. Our intelligent routing ensures you always get top-tier responses while optimizing for cost and performance."
      },
      {
        question: "How do I get started with LLMHive?",
        answer: "Simply sign up for a FREE account, which gives you UNLIMITED queries using our patented orchestration that beats most paid models. Once logged in, you can start chatting immediately. For #1 quality in ALL categories, upgrade to Lite ($14.99/mo), Pro ($29.99/mo), or Enterprise."
      },
      {
        question: "What makes LLMHive different from using ChatGPT or Claude directly?",
        answer: "LLMHive intelligently routes each query to the optimal model based on the task type. For coding, we might use Claude; for analysis, GPT-4o; for creative writing, Gemini. This ensures you always get the best response without manually switching between platforms."
      },
      {
        question: "Do I need API keys to use LLMHive?",
        answer: "No! LLMHive handles all the API connections for you. Simply subscribe to a plan and start using the platform. We manage the complexity of multiple AI providers behind the scenes."
      }
    ]
  },
  {
    id: "billing",
    name: "Billing & Plans",
    icon: <CreditCard className="h-5 w-5" />,
    faqs: [
      {
        question: "What plans are available?",
        answer: "We offer FREE (forever, UNLIMITED queries with patented orchestration that beats most paid models), Lite ($14.99/month, 100 ELITE queries #1 in ALL categories), Pro ($29.99/month, 500 ELITE queries + API access), and Enterprise ($35/seat/month, min 5 seats, SSO & compliance)."
      },
      {
        question: "What happens when I reach my ELITE query limit?",
        answer: "When you exhaust your ELITE queries, you'll automatically be throttled to our FREE tier orchestration. Our FREE tier still beats most single paid models thanks to our patented multi-model orchestration. You can upgrade your plan anytime to get more ELITE queries."
      },
      {
        question: "Can I upgrade or downgrade my plan at any time?",
        answer: "Yes! You can change your plan at any time. Upgrades take effect immediately with prorated billing. Downgrades take effect at the start of your next billing cycle."
      },
      {
        question: "Do you offer refunds?",
        answer: "We offer a 7-day money-back guarantee for first-time subscribers. If you're not satisfied, contact support within 7 days of your first payment for a full refund."
      },
      {
        question: "What payment methods do you accept?",
        answer: "We accept all major credit cards (Visa, MasterCard, American Express, Discover) through our secure Stripe payment processing. Enterprise customers can also pay via invoice."
      }
    ]
  },
  {
    id: "security",
    name: "Security & Privacy",
    icon: <Shield className="h-5 w-5" />,
    faqs: [
      {
        question: "Is my data secure?",
        answer: "Yes. We use industry-standard encryption for all data in transit (TLS 1.3) and at rest (AES-256). We never train AI models on your data, and your conversations are private to your account."
      },
      {
        question: "Do you store my conversations?",
        answer: "We temporarily process your queries to route them to AI models, but we don't permanently store conversation content. Usage metadata (token counts, timestamps) is retained for billing and analytics."
      },
      {
        question: "Are you SOC 2 compliant?",
        answer: "We're currently pursuing SOC 2 Type II certification. Enterprise customers can request our security documentation and compliance reports by contacting info@llmhive.ai."
      },
      {
        question: "Can I delete my data?",
        answer: "Yes. You can request complete data deletion through your account settings or by contacting support. We'll remove all your data within 30 days of the request."
      }
    ]
  },
  {
    id: "features",
    name: "Features & Usage",
    icon: <Settings className="h-5 w-5" />,
    faqs: [
      {
        question: "What is 'ELITE' orchestration?",
        answer: "ELITE orchestration uses our most sophisticated routing algorithm to select from top-tier models (GPT-4o, Claude 3.5 Sonnet, Gemini Pro, etc.) based on your specific query type. It consistently delivers #1 ranked performance across all categories."
      },
      {
        question: "How does the model routing work?",
        answer: "Our AI analyzes your query to determine the optimal model. Coding questions might route to Claude or Codex, creative writing to Gemini, factual queries to GPT-4o. This happens automatically in milliseconds."
      },
      {
        question: "Can I specify which model to use?",
        answer: "Pro and higher plans allow model preferences. However, we recommend using our intelligent routing for best results—that's the core value of LLMHive!"
      },
      {
        question: "Do you support image and file uploads?",
        answer: "Yes! Pro and higher plans support multimodal inputs including images, PDFs, and documents. The orchestrator automatically routes to vision-capable models when needed."
      },
      {
        question: "What's the maximum context length?",
        answer: "Context limits vary by plan: Free (8K tokens), Lite (25K tokens), Pro (100K tokens), Enterprise (200K+ tokens with extended context models)."
      }
    ]
  },
  {
    id: "enterprise",
    name: "Enterprise",
    icon: <BookOpen className="h-5 w-5" />,
    faqs: [
      {
        question: "What's included in the Enterprise plan?",
        answer: "Enterprise includes team management, SSO integration, dedicated support, custom SLAs, audit logs, compliance features, and 300 ELITE queries per seat per month. Minimum 5 seats required."
      },
      {
        question: "Can we get a custom contract?",
        answer: "Yes! Enterprise customers can negotiate custom terms, SLAs, pricing, and features. Contact info@llmhive.ai to discuss your needs."
      },
      {
        question: "Do you offer on-premise deployment?",
        answer: "We're developing an on-premise solution for highly regulated industries. Contact our enterprise team to discuss your requirements and join the waitlist."
      },
      {
        question: "What SSO providers do you support?",
        answer: "We support SAML 2.0 and OpenID Connect, compatible with Okta, Azure AD, Google Workspace, and most major identity providers."
      }
    ]
  }
]

function FAQAccordion({ faq, isOpen, onToggle }: { 
  faq: FAQItem
  isOpen: boolean
  onToggle: () => void 
}) {
  return (
    <div className="border-b border-border last:border-b-0">
      <button
        onClick={onToggle}
        className="w-full py-4 flex items-start justify-between text-left hover:text-[var(--bronze)] transition-colors"
      >
        <span className="font-medium pr-4">{faq.question}</span>
        {isOpen ? (
          <ChevronUp className="h-5 w-5 flex-shrink-0 text-[var(--bronze)]" />
        ) : (
          <ChevronDown className="h-5 w-5 flex-shrink-0 text-muted-foreground" />
        )}
      </button>
      {isOpen && (
        <div className="pb-4 text-muted-foreground text-sm leading-relaxed">
          {faq.answer}
        </div>
      )}
    </div>
  )
}

export default function HelpCenterPage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [openFAQs, setOpenFAQs] = useState<Set<string>>(new Set())
  const [activeCategory, setActiveCategory] = useState<string | null>(null)

  const toggleFAQ = (categoryId: string, index: number) => {
    const key = `${categoryId}-${index}`
    setOpenFAQs(prev => {
      const next = new Set(prev)
      if (next.has(key)) {
        next.delete(key)
      } else {
        next.add(key)
      }
      return next
    })
  }

  // Filter FAQs by search query
  const filteredCategories = faqCategories.map(category => ({
    ...category,
    faqs: category.faqs.filter(faq => 
      searchQuery === "" ||
      faq.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
      faq.answer.toLowerCase().includes(searchQuery.toLowerCase())
    )
  })).filter(category => category.faqs.length > 0)

  const displayedCategories = activeCategory
    ? filteredCategories.filter(c => c.id === activeCategory)
    : filteredCategories

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card/50 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center gap-4">
          <Link href="/">
            <Button variant="ghost" size="sm" className="gap-2">
              <ArrowLeft className="h-4 w-4" />
              Back to Home
            </Button>
          </Link>
        </div>
      </header>

      {/* Hero */}
      <div className="bg-gradient-to-b from-[var(--bronze)]/5 to-transparent py-16">
        <div className="max-w-3xl mx-auto px-4 text-center">
          <div className="w-16 h-16 rounded-full bg-[var(--bronze)]/10 flex items-center justify-center mx-auto mb-6">
            <HelpCircle className="h-8 w-8 text-[var(--bronze)]" />
          </div>
          <h1 className="text-4xl font-bold mb-4">Help Center</h1>
          <p className="text-lg text-muted-foreground mb-8">
            Find answers to common questions or reach out to our support team.
          </p>
          
          {/* Search */}
          <div className="relative max-w-xl mx-auto">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <Input
              placeholder="Search for answers..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-12 h-12 text-lg bg-card border-border"
            />
          </div>
        </div>
      </div>

      {/* Category Navigation */}
      <div className="border-b border-border">
        <div className="max-w-6xl mx-auto px-4">
          <div className="flex gap-2 py-4 overflow-x-auto">
            <Button
              variant={activeCategory === null ? "default" : "outline"}
              size="sm"
              onClick={() => setActiveCategory(null)}
              className={activeCategory === null ? "bg-[var(--bronze)] hover:bg-[var(--bronze)]/90" : ""}
            >
              All Topics
            </Button>
            {faqCategories.map(category => (
              <Button
                key={category.id}
                variant={activeCategory === category.id ? "default" : "outline"}
                size="sm"
                onClick={() => setActiveCategory(category.id)}
                className={`gap-2 ${activeCategory === category.id ? "bg-[var(--bronze)] hover:bg-[var(--bronze)]/90" : ""}`}
              >
                {category.icon}
                {category.name}
              </Button>
            ))}
          </div>
        </div>
      </div>

      {/* FAQ Content */}
      <main className="max-w-6xl mx-auto px-4 py-12">
        {displayedCategories.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground mb-4">No results found for &quot;{searchQuery}&quot;</p>
            <Button variant="outline" onClick={() => setSearchQuery("")}>
              Clear Search
            </Button>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-8">
            {displayedCategories.map(category => (
              <div key={category.id} className="bg-card border border-border rounded-xl p-6">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 rounded-lg bg-[var(--bronze)]/10 flex items-center justify-center text-[var(--bronze)]">
                    {category.icon}
                  </div>
                  <h2 className="text-xl font-semibold">{category.name}</h2>
                </div>
                <div className="divide-y divide-border">
                  {category.faqs.map((faq, index) => (
                    <FAQAccordion
                      key={index}
                      faq={faq}
                      isOpen={openFAQs.has(`${category.id}-${index}`)}
                      onToggle={() => toggleFAQ(category.id, index)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Still Need Help */}
        <div className="mt-16 bg-gradient-to-br from-[var(--bronze)]/10 to-transparent border border-[var(--bronze)]/20 rounded-2xl p-8 text-center">
          <h2 className="text-2xl font-bold mb-2">Still need help?</h2>
          <p className="text-muted-foreground mb-6">
            Our support team is here to assist you. Get a response within 24 hours.
          </p>
          <div className="flex flex-wrap gap-4 justify-center">
            <Link href="/contact">
              <Button className="bg-[var(--bronze)] hover:bg-[var(--bronze)]/90 gap-2">
                <MessageSquare className="h-4 w-4" />
                Contact Support
              </Button>
            </Link>
            <a href="mailto:info@llmhive.ai">
              <Button variant="outline" className="gap-2">
                <ExternalLink className="h-4 w-4" />
                Email Us
              </Button>
            </a>
          </div>
        </div>

        {/* Quick Links */}
        <div className="mt-12 grid md:grid-cols-3 gap-6">
          <Link 
            href="/demo" 
            className="group bg-card border border-border rounded-xl p-6 hover:border-[var(--bronze)]/50 transition-colors"
          >
            <BookOpen className="h-8 w-8 text-[var(--bronze)] mb-4" />
            <h3 className="font-semibold mb-2 group-hover:text-[var(--bronze)] transition-colors">
              Watch Demo
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              See LLMHive in action with our product walkthrough.
            </p>
            <span className="text-sm text-[var(--bronze)] flex items-center gap-1">
              Watch Now <ArrowRight className="h-4 w-4" />
            </span>
          </Link>

          <Link 
            href="/pricing" 
            className="group bg-card border border-border rounded-xl p-6 hover:border-[var(--bronze)]/50 transition-colors"
          >
            <CreditCard className="h-8 w-8 text-[var(--bronze)] mb-4" />
            <h3 className="font-semibold mb-2 group-hover:text-[var(--bronze)] transition-colors">
              Pricing Plans
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              Compare plans and find the right fit for your needs.
            </p>
            <span className="text-sm text-[var(--bronze)] flex items-center gap-1">
              View Plans <ArrowRight className="h-4 w-4" />
            </span>
          </Link>

          <Link 
            href="/billing" 
            className="group bg-card border border-border rounded-xl p-6 hover:border-[var(--bronze)]/50 transition-colors"
          >
            <Settings className="h-8 w-8 text-[var(--bronze)] mb-4" />
            <h3 className="font-semibold mb-2 group-hover:text-[var(--bronze)] transition-colors">
              Account Settings
            </h3>
            <p className="text-sm text-muted-foreground mb-4">
              Manage your subscription, usage, and preferences.
            </p>
            <span className="text-sm text-[var(--bronze)] flex items-center gap-1">
              Manage Account <ArrowRight className="h-4 w-4" />
            </span>
          </Link>
        </div>
      </main>
    </div>
  )
}
