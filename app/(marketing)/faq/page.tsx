import Link from "next/link"
import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "FAQ - LLMHive",
  description:
    "Get clear answers on LLMHive pricing, security, comparisons, and how multi-model AI orchestration works.",
  alternates: {
    canonical: "https://www.llmhive.ai/faq",
  },
  openGraph: {
    title: "LLMHive FAQ",
    description:
      "Get clear answers on LLMHive pricing, security, comparisons, and how multi-model AI orchestration works.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "LLMHive FAQ",
    description:
      "Get clear answers on LLMHive pricing, security, comparisons, and how multi-model AI orchestration works.",
  },
}

const faqItems = [
  {
    question: "What is LLMHive?",
    answer:
      "LLMHive is a multi-model AI orchestration platform that routes each request to the best AI model for accuracy, speed, and cost. Teams get one interface to 400+ models with enterprise security and usage controls.",
  },
  {
    question: "How is LLMHive different from ChatGPT or Claude?",
    answer:
      "Single-model tools answer with one model. LLMHive evaluates your task and routes it to the optimal model, or combines results from multiple models, so quality stays high across use cases while cost and latency remain predictable.",
  },
  {
    question: "Which AI models does LLMHive support?",
    answer:
      "LLMHive supports leading models across major providers including OpenAI, Anthropic, Google, Meta, and more. You get unified access through one interface and API.",
  },
  {
    question: "Is LLMHive secure for enterprise use?",
    answer:
      "Yes. LLMHive provides enterprise-grade security, encryption, and access controls. Enterprise plans include SSO, audit logs, and dedicated support.",
  },
  {
    question: "What pricing plans are available?",
    answer:
      "LLMHive offers Free, Lite, Pro, and Enterprise plans. Each plan includes multi-model orchestration with different ELITE query limits and enterprise controls.",
  },
  {
    question: "What happens after I use my ELITE queries?",
    answer:
      "Once ELITE queries are exhausted, LLMHive continues running on free-tier orchestration so work never stops.",
  },
  {
    question: "Do you offer a free plan?",
    answer:
      "Yes. The Free plan includes multi-model orchestration and unlimited queries on the free tier.",
  },
  {
    question: "Can I change plans any time?",
    answer:
      "Yes. You can upgrade or downgrade at any time with prorated billing for upgrades.",
  },
  {
    question: "What is multi-model AI orchestration?",
    answer:
      "Multi-model orchestration is the process of selecting and routing a request to the best AI model based on task type, quality, speed, and cost. It removes the need to switch tools manually.",
  },
  {
    question: "Does LLMHive support RAG and knowledge bases?",
    answer:
      "Yes. LLMHive supports retrieval-augmented generation (RAG) and knowledge bases so teams can answer questions using their own data.",
  },
]

function renderStructuredData() {
  const structuredData = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "FAQPage",
        mainEntity: faqItems.map((item) => ({
          "@type": "Question",
          name: item.question,
          acceptedAnswer: {
            "@type": "Answer",
            text: item.answer,
          },
        })),
      },
      {
        "@type": "ItemList",
        name: "FAQ Snapshot",
        itemListElement: [
          { "@type": "ListItem", position: 1, name: "What is LLMHive?" },
          { "@type": "ListItem", position: 2, name: "Pricing and plans" },
          { "@type": "ListItem", position: 3, name: "Security and governance" },
          { "@type": "ListItem", position: 4, name: "Multi-model orchestration" },
        ],
      },
      {
        "@type": "BreadcrumbList",
        itemListElement: [
          {
            "@type": "ListItem",
            position: 1,
            name: "FAQ",
            item: "https://www.llmhive.ai/faq",
          },
        ],
      },
    ],
  }

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
    />
  )
}

export default function FAQPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      {renderStructuredData()}
      <header className="border-b border-border/50 bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-4 py-6">
          <h1 className="text-3xl md:text-4xl font-bold">LLMHive FAQ</h1>
          <p className="mt-2 text-muted-foreground">
            Clear answers on pricing, security, and how our multi-model orchestration works.
          </p>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-12">
        <div className="grid gap-6">
          {faqItems.map((item) => (
            <section key={item.question} className="rounded-2xl border border-border/60 bg-card/40 p-6">
              <h2 className="text-lg font-semibold">{item.question}</h2>
              <p className="mt-3 text-sm text-muted-foreground leading-relaxed">{item.answer}</p>
            </section>
          ))}
        </div>

        <section className="mt-12 rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">FAQ Snapshot</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            A quick view of the most requested answers.
          </p>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm text-muted-foreground">
              <thead>
                <tr className="border-b border-border/60 text-left">
                  <th className="py-2 pr-4 text-foreground">Topic</th>
                  <th className="py-2 text-foreground">What you’ll learn</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-border/30">
                  <td className="py-2 pr-4">Platform Overview</td>
                  <td className="py-2">What LLMHive is and how it works</td>
                </tr>
                <tr className="border-b border-border/30">
                  <td className="py-2 pr-4">Pricing</td>
                  <td className="py-2">Plans, limits, and upgrades</td>
                </tr>
                <tr className="border-b border-border/30">
                  <td className="py-2 pr-4">Security</td>
                  <td className="py-2">Enterprise controls and governance</td>
                </tr>
                <tr>
                  <td className="py-2 pr-4">Orchestration</td>
                  <td className="py-2">Model routing and quality optimization</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section className="mt-12 rounded-2xl border border-border/60 bg-card/40 p-6">
          <h2 className="text-xl font-semibold">Explore More</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Dive deeper with comparisons, use cases, and role-based guides.
          </p>
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <Link href="/comparisons" className="text-[var(--bronze)]">
              Comparisons →
            </Link>
            <Link href="/use-cases" className="text-[var(--bronze)]">
              Use Cases →
            </Link>
            <Link href="/best-ai-assistant-for" className="text-[var(--bronze)]">
              Best AI Assistant For →
            </Link>
            <Link href="/case-studies" className="text-[var(--bronze)]">
              Case Studies →
            </Link>
          </div>
        </section>
      </main>
    </div>
  )
}
