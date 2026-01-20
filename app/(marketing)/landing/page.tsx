"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { 
  Sparkles, 
  Zap, 
  Shield, 
  BarChart3, 
  ArrowRight,
  Check,
  MessageSquare,
  Brain,
  Layers,
  Globe,
  Clock,
  Lock
} from "lucide-react"

const features = [
  {
    icon: Brain,
    title: "Multi-Model Orchestration",
    description: "Route queries to the best AI model automatically. GPT-5.2, Claude 4.5, Gemini 3, DeepSeek V3.2, and 400+ more—all in one place."
  },
  {
    icon: Layers,
    title: "Smart Model Selection",
    description: "Our HRM protocol analyzes your query and selects the optimal model based on task type, complexity, and cost."
  },
  {
    icon: Zap,
    title: "Lightning Fast",
    description: "Parallel model querying and intelligent caching deliver responses in milliseconds, not seconds."
  },
  {
    icon: Shield,
    title: "Enterprise Security",
    description: "SOC 2 compliant infrastructure with end-to-end encryption. Your data never trains our models."
  },
  {
    icon: BarChart3,
    title: "Cost Optimization",
    description: "Save up to 60% on AI costs with smart routing that balances quality and price."
  },
  {
    icon: Globe,
    title: "400+ Models",
    description: "Access to every major AI provider including OpenAI, Anthropic, Google, Meta, Mistral, and more through a single interface."
  }
]

const tiers = [
  {
    name: "Lite",
    price: "$9.99",
    period: "/month",
    description: "Get started with #1 quality AI",
    features: [
      "100 ELITE queries (#1 in ALL)",
      "400 BUDGET queries after quota",
      "Knowledge Base access",
      "Email support"
    ],
    cta: "Get Started",
    href: "/sign-up",
    highlighted: false
  },
  {
    name: "Pro",
    price: "$29.99",
    period: "/month",
    description: "Full power for professionals",
    features: [
      "500 ELITE queries (#1 in ALL)",
      "1,500 STANDARD queries (#1 in 8)",
      "Full API access",
      "DeepConf & Prompt Diffusion",
      "Priority support"
    ],
    cta: "Start Free Trial",
    href: "/sign-up",
    highlighted: true
  },
  {
    name: "Enterprise",
    price: "$35",
    period: "/seat/mo",
    description: "For teams with compliance needs",
    features: [
      "Min 5 seats ($175+/mo)",
      "400 ELITE/seat + 400 STANDARD/seat",
      "SSO & SAML integration",
      "SOC 2 compliance",
      "Dedicated support"
    ],
    cta: "Contact Sales",
    href: "/contact",
    highlighted: false
  },
  {
    name: "Maximum",
    price: "$99",
    period: "/month",
    description: "Never throttled, always best",
    features: [
      "1,000 MAXIMUM queries",
      "Beats GPT-5.2 & Claude 4.5",
      "Never throttled",
      "Premium orchestration",
      "Concierge support"
    ],
    cta: "Go Maximum",
    href: "/sign-up",
    highlighted: false
  }
]

const stats = [
  { value: "10M+", label: "Messages Processed" },
  { value: "99.9%", label: "Uptime" },
  { value: "150ms", label: "Avg Response Time" },
  { value: "400+", label: "AI Models" },
]

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-black via-zinc-950 to-black text-white">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-black/50 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
                <Sparkles className="h-5 w-5 text-white" />
              </div>
              <span className="text-xl font-bold tracking-tight">LLMHive</span>
            </div>
            <div className="hidden md:flex items-center gap-8">
              <Link href="#features" className="text-sm text-zinc-400 hover:text-white transition-colors">
                Features
              </Link>
              <Link href="#pricing" className="text-sm text-zinc-400 hover:text-white transition-colors">
                Pricing
              </Link>
              <Link href="/about" className="text-sm text-zinc-400 hover:text-white transition-colors">
                About
              </Link>
              <Link href="/contact" className="text-sm text-zinc-400 hover:text-white transition-colors">
                Contact
              </Link>
            </div>
            <div className="flex items-center gap-3">
              <Link href="/sign-in">
                <Button variant="ghost" size="sm" className="text-zinc-300 hover:text-white">
                  Sign In
                </Button>
              </Link>
              <Link href="/sign-up">
                <Button size="sm" className="bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white border-0">
                  Get Started
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-4xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/20 text-amber-400 text-sm mb-8">
              <Sparkles className="h-4 w-4" />
              <span>Now with GPT-5.2, Claude 4.5 Opus, Gemini 3 & Llama 4</span>
            </div>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 bg-gradient-to-r from-white via-zinc-200 to-zinc-400 bg-clip-text text-transparent">
              One Interface.<br />Every AI Model.
            </h1>
            <p className="text-xl text-zinc-400 mb-10 max-w-2xl mx-auto leading-relaxed">
              Stop switching between ChatGPT, Claude, and Gemini. LLMHive intelligently routes 
              your queries to the best AI model for each task—automatically.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link href="/sign-up">
                <Button size="lg" className="bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white border-0 text-lg px-8 h-14">
                  Start for Free
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
              <Link href="/">
                <Button size="lg" variant="outline" className="border-zinc-700 text-white hover:bg-zinc-900 text-lg px-8 h-14">
                  <MessageSquare className="mr-2 h-5 w-5" />
                  Try Demo
                </Button>
              </Link>
            </div>
          </div>

          {/* Stats */}
          <div className="mt-20 grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="text-4xl font-bold text-amber-500 mb-2">{stat.value}</div>
                <div className="text-sm text-zinc-500">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-24 px-4 sm:px-6 lg:px-8 bg-zinc-950/50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold mb-4">
              Why Teams Choose LLMHive
            </h2>
            <p className="text-xl text-zinc-400 max-w-2xl mx-auto">
              Enterprise-grade AI orchestration that just works.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature) => (
              <div 
                key={feature.title}
                className="p-6 rounded-2xl bg-zinc-900/50 border border-zinc-800 hover:border-amber-500/30 transition-colors group"
              >
                <div className="w-12 h-12 rounded-xl bg-amber-500/10 flex items-center justify-center mb-4 group-hover:bg-amber-500/20 transition-colors">
                  <feature.icon className="h-6 w-6 text-amber-500" />
                </div>
                <h3 className="text-xl font-semibold mb-2">{feature.title}</h3>
                <p className="text-zinc-400 leading-relaxed">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="py-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold mb-4">
              How It Works
            </h2>
            <p className="text-xl text-zinc-400 max-w-2xl mx-auto">
              Three simple steps to AI superpowers.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                step: "01",
                title: "Ask Anything",
                description: "Type your question or task into the unified chat interface. No need to choose a model."
              },
              {
                step: "02",
                title: "Smart Routing",
                description: "Our HRM protocol analyzes your query and routes it to the optimal AI model automatically."
              },
              {
                step: "03",
                title: "Get Results",
                description: "Receive the best possible answer, with transparency about which model was used and why."
              }
            ].map((item, i) => (
              <div key={item.step} className="relative">
                <div className="text-7xl font-bold text-zinc-800 mb-4">{item.step}</div>
                <h3 className="text-xl font-semibold mb-2">{item.title}</h3>
                <p className="text-zinc-400">{item.description}</p>
                {i < 2 && (
                  <div className="hidden md:block absolute top-8 right-0 w-1/3 h-px bg-gradient-to-r from-zinc-700 to-transparent" />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-24 px-4 sm:px-6 lg:px-8 bg-zinc-950/50">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold mb-4">
              Simple, Transparent Pricing
            </h2>
            <p className="text-xl text-zinc-400 max-w-2xl mx-auto">
              Start free, scale as you grow. No hidden fees.
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {tiers.map((tier) => (
              <div 
                key={tier.name}
                className={`relative p-8 rounded-2xl ${
                  tier.highlighted 
                    ? "bg-gradient-to-b from-amber-500/10 to-orange-600/5 border-2 border-amber-500/50" 
                    : "bg-zinc-900/50 border border-zinc-800"
                }`}
              >
                {tier.highlighted && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 bg-gradient-to-r from-amber-500 to-orange-600 rounded-full text-sm font-medium">
                    Most Popular
                  </div>
                )}
                <div className="mb-6">
                  <h3 className="text-xl font-semibold mb-2">{tier.name}</h3>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-bold">{tier.price}</span>
                    {tier.period && <span className="text-zinc-400">{tier.period}</span>}
                  </div>
                  <p className="text-sm text-zinc-400 mt-2">{tier.description}</p>
                </div>
                <ul className="space-y-3 mb-8">
                  {tier.features.map((feature) => (
                    <li key={feature} className="flex items-center gap-3 text-sm">
                      <Check className="h-4 w-4 text-amber-500 flex-shrink-0" />
                      <span className="text-zinc-300">{feature}</span>
                    </li>
                  ))}
                </ul>
                <Link href={tier.href}>
                  <Button 
                    className={`w-full ${
                      tier.highlighted 
                        ? "bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white border-0" 
                        : "bg-zinc-800 hover:bg-zinc-700 text-white"
                    }`}
                  >
                    {tier.cta}
                  </Button>
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Trust Badges */}
      <section className="py-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-wrap items-center justify-center gap-12 opacity-50">
            <div className="flex items-center gap-2">
              <Lock className="h-5 w-5" />
              <span className="text-sm">SOC 2 Compliant</span>
            </div>
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5" />
              <span className="text-sm">GDPR Ready</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              <span className="text-sm">99.9% Uptime SLA</span>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl md:text-5xl font-bold mb-6">
            Ready to supercharge your AI workflow?
          </h2>
          <p className="text-xl text-zinc-400 mb-10">
            Join thousands of developers and teams using LLMHive to build smarter, faster.
          </p>
          <Link href="/sign-up">
            <Button size="lg" className="bg-gradient-to-r from-amber-500 to-orange-600 hover:from-amber-600 hover:to-orange-700 text-white border-0 text-lg px-8 h-14">
              Get Started for Free
              <ArrowRight className="ml-2 h-5 w-5" />
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-800 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-8">
            <div>
              <h4 className="font-semibold mb-4">Product</h4>
              <ul className="space-y-2 text-sm text-zinc-400">
                <li><Link href="#features" className="hover:text-white transition-colors">Features</Link></li>
                <li><Link href="#pricing" className="hover:text-white transition-colors">Pricing</Link></li>
                <li><Link href="/models" className="hover:text-white transition-colors">Models</Link></li>
                <li><Link href="/discover" className="hover:text-white transition-colors">Discover</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Company</h4>
              <ul className="space-y-2 text-sm text-zinc-400">
                <li><Link href="/about" className="hover:text-white transition-colors">About</Link></li>
                <li><Link href="/contact" className="hover:text-white transition-colors">Contact</Link></li>
                <li><Link href="/careers" className="hover:text-white transition-colors">Careers</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Legal</h4>
              <ul className="space-y-2 text-sm text-zinc-400">
                <li><Link href="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link></li>
                <li><Link href="/terms" className="hover:text-white transition-colors">Terms of Service</Link></li>
              </ul>
            </div>
            <div>
              <h4 className="font-semibold mb-4">Support</h4>
              <ul className="space-y-2 text-sm text-zinc-400">
                <li><Link href="/contact" className="hover:text-white transition-colors">Help Center</Link></li>
                <li><a href="mailto:support@llmhive.ai" className="hover:text-white transition-colors">support@llmhive.ai</a></li>
              </ul>
            </div>
          </div>
          <div className="flex flex-col md:flex-row items-center justify-between pt-8 border-t border-zinc-800">
            <div className="flex items-center gap-2 mb-4 md:mb-0">
              <div className="w-6 h-6 rounded bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
                <Sparkles className="h-4 w-4 text-white" />
              </div>
              <span className="font-semibold">LLMHive</span>
            </div>
            <p className="text-sm text-zinc-500">
              © 2026 LLMHive. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}

